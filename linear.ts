/**
 * workers/seo-generator/src/linear.ts — versión mejorada
 *
 * CAMBIOS clave vs. la versión anterior:
 *
 *   1) Topic ya se envía en el POST (esto ya funcionaba), PERO añadimos
 *      verificación post-create: si el item creado NO trajo las taxonomies
 *      aplicadas, hacemos PATCH de respaldo (por slug, no por ULID).
 *
 *   2) hero_image opcional en el momento del create — si recibes un
 *      `heroImage` en el KeywordInput (vía /generate o /auto con override),
 *      se incluye en `data.hero_image` desde el POST inicial, sin necesidad
 *      del PATCH posterior.
 *
 *   3) PATCH de actualización SIEMPRE por SLUG (no por ULID). Documentado
 *      en clivi-blog AGENTS.md: "entry.id is the slug (for URLs).
 *      entry.data.id is the database ULID".
 *
 *   4) Logging mejorado para ver fácilmente si topic / hero_image quedaron
 *      bien aplicados después del create.
 *
 *   5) Resolución de autores: si el ULID real existe, lo usa; si no,
 *      fallback al seed. Sin cambios funcionales.
 */

import type {
	GeneratedArticle,
	KeywordInput,
	LinearIssueResult,
	WorkerEnv,
} from "./types";

// ─── Autores ─────────────────────────────────────────────────────────────────

const SEED_AUTHOR_ULIDS: Record<string, string> = {
	"mariana-solis": "author-mariana-solis",
	"ivan-pereda":   "author-ivan-pereda",
	"paola-vargas":  "author-paola-vargas",
	"javier-romero": "author-javier-romero",
};

// Médicos reales — completa los ULIDs cuando crees sus perfiles en Emdash prod.
const REAL_AUTHOR_ULIDS: Record<string, string> = {
	"bernardo-diaz":    "01KQWXP74ZCXV94Z2RY200CCJK",
	"darielle-aguilar": "",
	"oscar-bazan":      "",
	"ivanka-reyes":     "",
};

const CATEGORY_AUTHORS: Record<string, string> = {
	"glucosa":    "bernardo-diaz",
	"pulse":      "bernardo-diaz",
	"citas":      "darielle-aguilar",
	"body-scan":  "darielle-aguilar",
	"peso":       "oscar-bazan",
	"cintura":    "oscar-bazan",
	"journey":    "ivanka-reyes",
	"meal-plan":  "ivanka-reyes",
};

const CATEGORY_REVIEWERS: Record<string, string> = {
	"glucosa":    "darielle-aguilar",
	"pulse":      "oscar-bazan",
	"citas":      "bernardo-diaz",
	"body-scan":  "oscar-bazan",
	"peso":       "darielle-aguilar",
	"cintura":    "darielle-aguilar",
	"journey":    "oscar-bazan",
	"meal-plan":  "bernardo-diaz",
};

// Fallback a autores del seed cuando el ULID real está vacío.
const SEED_FALLBACKS: Record<string, string> = {
	"bernardo-diaz":    "author-mariana-solis",
	"darielle-aguilar": "author-mariana-solis",
	"oscar-bazan":      "author-ivan-pereda",
	"ivanka-reyes":     "author-ivan-pereda",
};

const CATEGORY_CTA: Record<string, "valoracion" | "newsletter" | "none"> = {
	"glucosa": "valoracion", "pulse": "valoracion",
	"citas": "valoracion",   "body-scan": "valoracion",
	"peso": "valoracion",    "cintura": "valoracion",
	"journey": "newsletter", "meal-plan": "newsletter",
};

let keyCounter = 0;
function nextKey(): string {
	keyCounter += 1;
	return `k${keyCounter.toString(36)}${Math.random().toString(36).slice(2, 5)}`;
}

function resolveUlid(slug: string): string {
	const real = REAL_AUTHOR_ULIDS[slug];
	if (real) return real;
	return SEED_FALLBACKS[slug] ?? "author-mariana-solis";
}

// ─── CREATE ──────────────────────────────────────────────────────────────────

export async function createLinearIssue(
	article: GeneratedArticle,
	kw: KeywordInput,
	env: WorkerEnv,
): Promise<LinearIssueResult> {

	const baseUrl      = env.EMDASH_BASE_URL.replace(/\/+$/, "");
	const token        = env.EMDASH_API_KEY;
	const authorSlug   = CATEGORY_AUTHORS[kw.topic]   ?? "bernardo-diaz";
	const reviewerSlug = CATEGORY_REVIEWERS[kw.topic] ?? "darielle-aguilar";
	const authorUlid   = resolveUlid(authorSlug);
	const reviewerUlid = resolveUlid(reviewerSlug);
	const ctaKind      = CATEGORY_CTA[kw.topic]       ?? "valoracion";
	const issueId      = `seo-${Date.now()}`;
	const blocks       = buildContentBlocks(article);

	// ── Hero image opcional desde el create ─────────────────────────────────
	// Si más adelante decides pre-cargar imágenes (por ejemplo, asignar la
	// imagen estática del topic ya subida a Emdash media), añade un campo
	// `heroImage?: { src, alt }` a KeywordInput y úsalo aquí.
	const heroImage =
		(kw as KeywordInput & { heroImage?: { src: string; alt?: string } }).heroImage;

	// ── POST: todo de una vez (taxonomies incluidas) ─────────────────────────
	const createPayload: Record<string, unknown> = {
		slug:   article.slug,
		status: "draft",
		data: {
			title:                   article.title,
			excerpt:                 article.metaDescription || article.title,
			variant:                 kw.variant ?? "article",
			content:                 blocks,
			author:                  authorUlid,
			medical_reviewer:        reviewerUlid,
			cta_kind:                ctaKind,
			reading_time_min:        Math.max(1, Math.ceil(article.wordCount / 200)),
			last_reviewed_at:        new Date().toISOString(),
			linear_issue_id:         issueId,
			linear_issue_identifier: issueId.toUpperCase(),
			ready_for_publish:       false,
			needs_categorization:    false,
			...(heroImage?.src
				? { hero_image: { src: heroImage.src, alt: heroImage.alt ?? article.imageAlt } }
				: {}),
			...(article.references.length > 0 ? { references_list: article.references } : {}),
			...(Object.keys(article.glossary).length > 0 ? { glossary: article.glossary } : {}),
		},
		taxonomies: {
			topic: [kw.topic],
			tag:   (kw.extra_tags ?? []).map(slugifyTag).filter(Boolean),
		},
		seo: {
			title:       article.seoTitle,
			description: article.metaDescription || "",
		},
	};

	const createRes = await fetch(`${baseUrl}/_emdash/api/content/posts`, {
		method: "POST",
		headers: {
			"content-type": "application/json",
			"authorization": `Bearer ${token}`,
		},
		body: JSON.stringify(createPayload),
	});

	const createText = await createRes.text();
	console.log("=== CREATE ===", createRes.status, createText.slice(0, 200));

	if (!createRes.ok) {
		throw new Error(`Emdash ${createRes.status}: ${createText}`);
	}

	let created: any;
	try { created = JSON.parse(createText); } catch { created = {}; }

	// El item devuelto:
	//   - created.data.item.id  → slug (entry id)
	//   - created.data.item.data.id → ULID de DB
	const item     = created?.data?.item ?? created?.data ?? created ?? {};
	const postSlug = item?.slug ?? article.slug;            // ← USAR ESTE para PATCH
	const postUlid = String(item?.data?.id ?? item?.id ?? "");

	console.log(`📝 Draft creado: slug=${postSlug}  ulid=${postUlid.slice(0, 8)}…`);

	// ── Verificación: ¿las taxonomies quedaron aplicadas? ───────────────────
	const appliedTopics = readTopics(item);
	if (!appliedTopics.includes(kw.topic)) {
		console.warn(
			`⚠️  topic "${kw.topic}" no quedó aplicado en el POST. Forzando PATCH…`,
		);
		await patchPostBySlug(baseUrl, token, postSlug, {
			taxonomies: { topic: [kw.topic] },
		});
	}

	return {
		id:         postUlid || postSlug,
		identifier: `EMDASH-${(postUlid || postSlug).slice(-6)}`,
		url:        `${baseUrl}/_emdash/admin/content/posts/${encodeURIComponent(postSlug)}`,
	};
}

// ─── PATCH helper — SIEMPRE por slug ─────────────────────────────────────────

export async function patchPostBySlug(
	baseUrl: string,
	token: string,
	slug: string,
	payload: {
		data?: Record<string, unknown>;
		taxonomies?: { topic?: string[]; tag?: string[] };
		status?: "draft" | "published";
	},
): Promise<{ ok: boolean; status: number; body: string }> {
	const url = `${baseUrl.replace(/\/+$/, "")}/_emdash/api/content/posts/${encodeURIComponent(slug)}`;
	const res = await fetch(url, {
		method: "PATCH",
		headers: {
			"content-type": "application/json",
			"authorization": `Bearer ${token}`,
		},
		body: JSON.stringify(payload),
	});
	const body = await res.text();
	if (!res.ok) {
		console.warn(`PATCH /posts/${slug} → ${res.status}: ${body.slice(0, 200)}`);
	}
	return { ok: res.ok, status: res.status, body };
}

function readTopics(item: any): string[] {
	const tax = item?.taxonomies ?? item?.data?.taxonomies ?? {};
	const topics = tax?.topic ?? [];
	if (!Array.isArray(topics)) return [];
	return topics
		.map((t: any) => (typeof t === "string" ? t : t?.slug ?? t?.name ?? ""))
		.filter(Boolean);
}

// ─── Construcción de bloques (sin cambios) ───────────────────────────────────

function buildContentBlocks(article: GeneratedArticle): object[] {
	const blocks: object[] = [];

	if (article.keyTakeaways.length > 0) {
		blocks.push({
			_type:  "key-takeaways",
			_key:   nextKey(),
			label:  "Lo esencial · 30 segundos",
			points: article.keyTakeaways,
		});
	}

	blocks.push(...markdownToBlocks(article.bodyMarkdown));

	if (article.evidenceNote) {
		blocks.push({
			_type: "evidence-note",
			_key:  nextKey(),
			label: "📊 Lo que dice la evidencia",
			body:  article.evidenceNote,
		});
	}

	return blocks;
}

function markdownToBlocks(md: string): object[] {
	const lines = md.replace(/\r\n/g, "\n").split("\n");
	const blocks: object[] = [];
	let i = 0;

	while (i < lines.length) {
		const line = lines[i];
		if (!line.trim()) { i++; continue; }

		if (/^#\s+/.test(line)) { i++; continue; }

		const hMatch = line.match(/^(#{2,4})\s+(.*)$/);
		if (hMatch) {
			const level = hMatch[1].length;
			const style = level === 2 ? "h2" : level === 3 ? "h3" : "h4";
			blocks.push({ _type: "block", _key: nextKey(), style, children: parseInline(hMatch[2]) });
			i++; continue;
		}

		if (line.startsWith("> ")) {
			const buf = [line.slice(2)];
			i++;
			while (i < lines.length && lines[i].startsWith("> ")) { buf.push(lines[i].slice(2)); i++; }
			blocks.push({ _type: "block", _key: nextKey(), style: "blockquote", children: parseInline(buf.join(" ")) });
			continue;
		}

		if (/^---+\s*$/.test(line) || /^\|.+\|$/.test(line.trim())) { i++; continue; }

		const bulletMatch = line.match(/^\s*[-*+]\s+(.*)$/);
		if (bulletMatch) {
			while (i < lines.length) {
				const m = lines[i].match(/^\s*[-*+]\s+(.*)$/);
				if (!m) break;
				blocks.push({ _type: "block", _key: nextKey(), style: "normal", listItem: "bullet", level: 1, children: parseInline(m[1]) });
				i++;
			}
			continue;
		}

		const numMatch = line.match(/^\s*\d+\.\s+(.*)$/);
		if (numMatch) {
			while (i < lines.length) {
				const m = lines[i].match(/^\s*\d+\.\s+(.*)$/);
				if (!m) break;
				blocks.push({ _type: "block", _key: nextKey(), style: "normal", listItem: "number", level: 1, children: parseInline(m[1]) });
				i++;
			}
			continue;
		}

		const buf = [line];
		i++;
		while (i < lines.length && lines[i].trim() && !lines[i].match(/^(#{1,6}\s+|>|\s*[-*+]\s+|\s*\d+\.\s+|---|\|)/)) {
			buf.push(lines[i]);
			i++;
		}
		blocks.push({ _type: "block", _key: nextKey(), style: "normal", children: parseInline(buf.join(" ")) });
	}

	return blocks;
}

function parseInline(text: string): object[] {
	const out: object[] = [];
	let cursor = 0;
	const re = /(\*\*([^*]+)\*\*|__([^_]+)__|\*([^*]+)\*|_([^_]+)_|`([^`]+)`)/g;
	let m: RegExpExecArray | null;
	while ((m = re.exec(text))) {
		if (m.index > cursor) out.push({ _type: "span", _key: nextKey(), text: text.slice(cursor, m.index), marks: [] });
		const full = m[0];
		if (full.startsWith("**") || full.startsWith("__")) {
			out.push({ _type: "span", _key: nextKey(), text: m[2] ?? m[3] ?? "", marks: ["strong"] });
		} else if (full.startsWith("*") || full.startsWith("_")) {
			out.push({ _type: "span", _key: nextKey(), text: m[4] ?? m[5] ?? "", marks: ["em"] });
		} else {
			out.push({ _type: "span", _key: nextKey(), text: m[6] ?? "", marks: ["code"] });
		}
		cursor = m.index + full.length;
	}
	if (cursor < text.length) out.push({ _type: "span", _key: nextKey(), text: text.slice(cursor), marks: [] });
	return out.length > 0 ? out : [{ _type: "span", _key: nextKey(), text, marks: [] }];
}

function slugifyTag(label: string): string {
	return label.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "")
		.replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "").slice(0, 60);
}
