/**
 * workers/seo-generator/src/index.ts
 *
 * Triggers:
 *   POST /{secret}/generate   → batch manual con keywords específicas
 *   POST /{secret}/auto       → batch automático desde el motor de keywords
 *   GET  /{secret}/universe   → ver el universo completo de keywords con scores
 *   Cron lunes 6am            → auto batch semanal
 */

import { generateArticle } from "./generator";
import { createLinearIssue } from "./linear";
import { generateKeywordBatch, getFullUniverse, scoreKeywords } from "./keyword-engine";
import type { KeywordInput, SeoJobResult, WorkerEnv } from "./types";

export default {
	async fetch(req: Request, env: WorkerEnv): Promise<Response> {
		const url = new URL(req.url);

		if (url.pathname === "/health") {
			return json({ ok: true, env: env.BLOG_ENV, version: "2.0" });
		}

		const secret = env.LINEAR_TRIGGER_SECRET;

		// ── Ver universo de keywords con scores ──────────────────────────────
		if (url.pathname === `/${secret}/universe`) {
			const universe = getFullUniverse();
			return json({ total: universe.length, keywords: universe });
		}

		// ── Batch automático desde el motor ──────────────────────────────────
		if (url.pathname === `/${secret}/auto` && req.method === "POST") {
			let body: { topics?: string[]; batchSize?: number; gscData?: unknown[] } = {};
			try { body = await req.json() as typeof body; } catch { body = {}; }

			const batch = generateKeywordBatch({
				topics:    body.topics as any,
				batchSize: body.batchSize ?? 10,
			});

			const results = await processKeywords(batch, env);
			const ok = results.filter((r) => r.status === "success").length;
			return json({ ok, total: results.length, results });
		}

		// ── Batch manual con keywords específicas ────────────────────────────
		if (url.pathname === `/${secret}/generate` && req.method === "POST") {
			let keywords: KeywordInput[];
			try {
				const body = (await req.json()) as { keywords?: unknown };
				if (!Array.isArray(body.keywords) || body.keywords.length === 0) {
					return json({ error: "keywords array requerido y no vacío" }, 400);
				}
				keywords = body.keywords as KeywordInput[];
			} catch {
				return json({ error: "JSON inválido" }, 400);
			}

			const results = await processKeywords(keywords, env);
			const ok = results.filter((r) => r.status === "success").length;
			return json({ ok, total: results.length, results });
		}

		return new Response("Not found", { status: 404 });
	},

	// ── Cron: lunes 6am UTC — batch semanal automático ───────────────────────
	async scheduled(_event: ScheduledEvent, env: WorkerEnv): Promise<void> {
		console.log("Cron: iniciando batch semanal automático");

		// Leer keywords publicadas para no duplicar
		let excludeSlugs: string[] = [];
		try {
			const raw = await env.KEYWORDS_KV.get("published-slugs");
			if (raw) excludeSlugs = JSON.parse(raw) as string[];
		} catch { /* ok */ }

		// Generar batch diversificado: 3 de glucosa, 3 de peso, 2 de meal-plan, 2 de journey
		const batch = generateKeywordBatch({
			batchSize:    10,
			excludeSlugs,
		});

		console.log(`Cron: ${batch.length} keywords seleccionadas`);
		const results = await processKeywords(batch, env);

		// Guardar reporte
		const ok = results.filter((r) => r.status === "success").length;
		const reportKey = `report-${new Date().toISOString().slice(0, 10)}`;
		await env.KEYWORDS_KV.put(reportKey, JSON.stringify({ ok, total: results.length, results }), {
			expirationTtl: 60 * 60 * 24 * 90,
		});

		console.log(`Cron: ${ok}/${results.length} exitosos. Reporte: ${reportKey}`);
	},
};

// ─────────────────────────────────────────────────────────────────────────────

async function processKeywords(keywords: KeywordInput[], env: WorkerEnv): Promise<SeoJobResult[]> {
	const results: SeoJobResult[] = [];

	for (const kw of keywords) {
		console.log(`[SEO] Procesando: "${kw.keyword}"`);
		try {
			const article = await generateArticle(kw, env.ANTHROPIC_API_KEY);
			console.log(`  ✅ Artículo generado: "${article.title}" (${article.wordCount} palabras)`);

			const issue = await createLinearIssue(article, kw, env);

			results.push({
				keyword:          kw.keyword,
				status:           "success",
				linearIdentifier: issue?.identifier || "EMDASH-OK",
				linearUrl:        issue?.url || "",
				articleTitle:     article.title,
				wordCount:        article.wordCount,
			});
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			console.error(`  ❌ Error: ${msg}`);
			results.push({ keyword: kw.keyword, status: "error", error: msg });
		}

		await sleep(1500);
	}

	return results;
}

function json(data: unknown, status = 200): Response {
	return new Response(JSON.stringify(data, null, 2), {
		status,
		headers: { "content-type": "application/json" },
	});
}

function sleep(ms: number): Promise<void> {
	return new Promise((r) => setTimeout(r, ms));
}
