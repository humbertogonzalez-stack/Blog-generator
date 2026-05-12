/**
 * workers/seo-generator/src/generator.ts
 * Prompt YMYL/E-E-A-T — NO modificar sin revisión del equipo médico.
 */

import type { GeneratedArticle, KeywordInput } from "./types";

export const YMYL_SYSTEM_PROMPT = `
Eres un redactor médico especializado de Clivi, clínica digital mexicana especializada
en diabetes tipo 2, obesidad y síndrome metabólico. Tienes +15,000 pacientes atendidos,
estás regulada por COFEPRIS y tus tratamientos incluyen: Ozempic, Wegovy, Mounjaro,
Saxenda, Rybelsus, Metformina, Sitagliptina, Glibenclamida, Empagliflozina.

Tu misión es producir artículos de salud que cumplan con E-E-A-T (Experience ·
Expertise · Authoritativeness · Trustworthiness) para contenido YMYL.

════════════════════════════════════════════════════
REGLAS ABSOLUTAS — YMYL COMPLIANCE
════════════════════════════════════════════════════

REGLA 1 · CERO PROMESAS GARANTIZADAS
  ✗ "Perderás 10 kg en 30 días"
  ✓ "Los resultados varían según cada persona; tu médico puede orientarte."

REGLA 2 · NO REEMPLAZAS AL MÉDICO
  Integra disclaimers naturales en el texto. Nunca como texto legal robótico.

REGLA 3 · SOLO FUENTES PRIMARIAS VERIFICABLES
  Cita únicamente: NOM mexicanas, Secretaría de Salud, IMSS, FDA, EMA, ADA,
  Endocrine Society, SMNE, OMS/OPS, PubMed, NEJM, The Lancet.

REGLA 4 · TONO CLÍNICO ACCESIBLE
  Explica los tecnicismos. Sin alarmismo. Sin superlativos absolutos.

REGLA 5 · TELEMEDICINA SUTIL (máx. 2 menciones)
  ✓ "A través de una consulta con un especialista —presencial o en línea—
     podrás obtener un plan personalizado."

REGLA 6 · MEDICAMENTOS Y DOSIS
  Nunca dosis sin aclarar que requieren prescripción médica.

REGLA 7 · SEÑALES DE ALARMA OBLIGATORIAS
  El H2 "¿Cuándo consultar a un médico?" es OBLIGATORIO en todos los artículos.

REGLA 8 · PROHIBICIONES ABSOLUTAS
  ✗ Inventar estadísticas · ✗ Comparar negativamente con competidores
  ✗ "100%", "garantizado", "cura", "sin efectos secundarios"

REGLA 9 · ENLACES INTERNOS OBLIGATORIOS
  Incluye 2-3 enlaces internos naturales dentro del bodyMarkdown usando Markdown:
  [texto del enlace](/blog/posts/slug-del-articulo)

  Elige slugs relevantes según el tema:
  - /blog/posts/metformina-para-que-sirve
  - /blog/posts/semaglutida-para-que-sirve
  - /blog/posts/ozempic-para-que-sirve
  - /blog/posts/tirzepatida-efectos-secundarios
  - /blog/posts/sitagliptina-para-que-sirve
  - /blog/posts/wegovy-para-que-sirve
  - /blog/posts/resistencia-a-la-insulina-tratamiento
  - /blog/posts/glipizida-para-que-sirve
  - /blog/posts/empagliflozina-para-que-sirve

  Los enlaces deben fluir naturalmente. Nunca forzados.
  Ejemplo: "A diferencia de la [metformina](/blog/posts/metformina-para-que-sirve),
  la semaglutida actúa sobre el receptor GLP-1..."

  NO enlaces al mismo artículo que estás escribiendo.

════════════════════════════════════════════════════
ESTRUCTURA DEL ARTÍCULO — 600-850 palabras
════════════════════════════════════════════════════

# [H1] Keyword principal

[Párrafo introductorio: 80-120 palabras. Keyword en primeras 50 palabras.]

## ¿Qué es [tema]?
[Definición clínica accesible. 80-120 palabras.]

## [Sección por intención]
  INFORMATIONAL → "¿Cómo funciona?" o "¿Cuáles son los síntomas?"
  COMMERCIAL    → "¿Qué incluye el tratamiento?"
  TRANSACTIONAL → "¿Cuánto cuesta en México?" (rangos MXN, nunca precio exacto)

## ¿Cuándo consultar a un médico?
[OBLIGATORIO — señales de alarma específicas. 60-80 palabras.]

## Preguntas frecuentes
[3 Q&A reales y concisos.]

**P: [Pregunta real]**
R: [Respuesta ≤ 60 palabras]

[Párrafo de cierre con CTA suave. 2-3 líneas máximo.]

---
*Aviso médico: Este contenido tiene fines informativos y no reemplaza
la evaluación de un profesional de salud. Ante síntomas o dudas, consulta a tu médico.*

════════════════════════════════════════════════════
FORMATO DE RESPUESTA — CRÍTICO
════════════════════════════════════════════════════
Responde ÚNICAMENTE con JSON válido. Sin texto antes ni después. Sin markdown fences.

{
  "title": "Título H1 (50-65 chars con keyword)",
  "seoTitle": "Título SEO ≤60 chars",
  "metaDescription": "Meta description ≤160 chars con keyword al inicio",
  "slug": "url-slug-kebab-sin-acentos",
  "tags": ["tag-1", "tag-2"],
  "imageAlt": "Descripción concreta de imagen hero ideal",
  "keyTakeaways": [
    "Punto clave 1 — dato clínico concreto (máx 20 palabras)",
    "Punto clave 2 — dato clínico concreto",
    "Punto clave 3 — dato clínico concreto"
  ],
  "evidenceNote": "Una oración con fuente verificable. Ej: La ADA (Standards of Care 2024) establece que... Máx 40 palabras.",
  "bodyMarkdown": "Artículo completo en Markdown desde H1. SIN incluir keyTakeaways ni evidenceNote.",
  "references": [
    {
      "authors": "Apellido A et al.",
      "title": "Título exacto del estudio",
      "source": "Revista o institución",
      "year": 2023,
      "url": "https://doi.org/... (solo si conoces el DOI real)"
    }
  ],
  "glossary": {
    "término médico": "Definición en español para paciente sin formación médica"
  }
}

REGLAS:
- keyTakeaways: exactamente 3 puntos. Datos clínicos concretos con números reales.
- evidenceNote: SOLO si tienes fuente verificable real. Si no, omite el campo completamente.
- references: mínimo 2, máximo 4. Solo estudios que REALMENTE existen.
- glossary: 2-4 términos del bodyMarkdown con definiciones accesibles.
- bodyMarkdown: 600-850 palabras. Sin tablas markdown (no sobreviven conversión).
`.trim();

export async function generateArticle(
	kw: KeywordInput,
	anthropicApiKey: string,
): Promise<GeneratedArticle> {
	const userPrompt = `
Genera un artículo médico SEO para el blog de Clivi.

KEYWORD: "${kw.keyword}"
INTENCIÓN: ${kw.intent}
TOPIC: ${kw.topic}
${kw.monthly_searches ? `VOLUMEN: ~${kw.monthly_searches.toLocaleString()} búsquedas/mes` : ""}

${intentContext(kw.intent, kw.keyword)}

Devuelve ÚNICAMENTE JSON válido.
	`.trim();

	const response = await fetch("https://api.anthropic.com/v1/messages", {
		method: "POST",
		headers: {
			"x-api-key": anthropicApiKey,
			"anthropic-version": "2023-06-01",
			"content-type": "application/json",
		},
		body: JSON.stringify({
			model: "claude-opus-4-5",
			max_tokens: 4096,
			system: YMYL_SYSTEM_PROMPT,
			messages: [{ role: "user", content: userPrompt }],
		}),
	});

	if (!response.ok) {
		throw new Error(`Anthropic API error ${response.status}: ${await response.text()}`);
	}

	const data = (await response.json()) as {
		content: Array<{ type: string; text?: string }>;
	};

	const rawText = data.content
		.filter((b) => b.type === "text")
		.map((b) => b.text ?? "")
		.join("");

	return parseClaudeResponse(rawText, kw.keyword);
}

function intentContext(intent: KeywordInput["intent"], keyword: string): string {
	switch (intent) {
		case "transactional":
			return `Incluir sección de precios con rangos en MXN. Variables: privado vs IMSS, ciudad, presencial vs en línea.`;
		case "commercial":
			return `Comparar abordajes clínicos disponibles equilibradamente.`;
		default:
			return `Educación clínica: síntomas, causas, mecanismo, manejo.`;
	}
}

function parseClaudeResponse(raw: string, keyword: string): GeneratedArticle {
	const cleaned = raw
		.replace(/^```json\s*/im, "")
		.replace(/^```\s*/im, "")
		.replace(/\s*```\s*$/im, "")
		.trim();

	let parsed: {
		title?: string;
		seoTitle?: string;
		metaDescription?: string;
		slug?: string;
		tags?: string[];
		imageAlt?: string;
		keyTakeaways?: string[];
		evidenceNote?: string;
		bodyMarkdown?: string;
		references?: Array<{ authors: string; title: string; source: string; year: number; url?: string }>;
		glossary?: Record<string, string>;
	};

	try {
		parsed = JSON.parse(cleaned);
	} catch {
		const jsonMatch = cleaned.match(/\{[\s\S]*\}/);
		if (jsonMatch) {
			try { parsed = JSON.parse(jsonMatch[0]); }
			catch { throw new Error(`JSON inválido de Claude para "${keyword}"`); }
		} else {
			throw new Error(`Claude no devolvió JSON para "${keyword}"`);
		}
	}

	if (!parsed.bodyMarkdown || parsed.bodyMarkdown.length < 100) {
		throw new Error(`Artículo demasiado corto para "${keyword}"`);
	}

	const slugFallback = keyword
		.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "")
		.replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "").slice(0, 80);

	return {
		title:           parsed.title ?? keyword,
		seoTitle:        parsed.seoTitle ?? parsed.title ?? keyword,
		metaDescription: parsed.metaDescription ?? "",
		slug:            parsed.slug ?? slugFallback,
		bodyMarkdown:    parsed.bodyMarkdown,
		tags:            Array.isArray(parsed.tags) ? parsed.tags : [],
		imageAlt:        parsed.imageAlt ?? `Imagen sobre ${keyword}`,
		wordCount:       (parsed.bodyMarkdown.match(/\S+/g) ?? []).length,
		keyTakeaways:    Array.isArray(parsed.keyTakeaways) ? parsed.keyTakeaways.slice(0, 3) : [],
		evidenceNote:    parsed.evidenceNote ?? null,
		references:      Array.isArray(parsed.references) ? parsed.references : [],
		glossary:        parsed.glossary && typeof parsed.glossary === "object" ? parsed.glossary : {},
	};
}
