/**
 * workers/seo-generator/src/keyword-engine.ts
 *
 * Motor de expansión de keywords para Clivi.
 * Genera listas de keywords priorizadas SIN depender de GSC ni APIs externas.
 * Se ancla 100% en la oferta real de Clivi.
 *
 * ─── ARQUITECTURA DE 3 NIVELES ───────────────────────────────────────────────
 *
 * NIVEL 1 — Pilares (4 topics del blog de Clivi)
 *   glucosa · peso · meal-plan · journey
 *
 * NIVEL 2 — Clusters semánticos (grupos de intención dentro de cada pilar)
 *   Cada cluster = un área de oportunidad SEO distinta
 *
 * NIVEL 3 — Keywords long tail
 *   Combinaciones específicas generadas por patrones semánticos
 *
 * ─── FÓRMULA DE SCORING ──────────────────────────────────────────────────────
 *
 *   Score = (Vol × 0.30) + (OpCTR × 0.25) + (PosZona × 0.20)
 *           + (IntentScore × 0.15) + (CliviRel × 0.10)
 *
 *   Vol         = volumen mensual estimado normalizado (0–100)
 *   OpCTR       = oportunidad de CTR = 100 − CTR_actual_estimado
 *                 (keywords nuevas sin artículo → OpCTR = 85 por defecto)
 *   PosZona     = pos 1-3→20, pos 4-10→100, pos 11-20→60, >20→10, sin dato→70
 *   IntentScore = transactional→100, commercial→70, informational→40
 *   CliviRel    = 1.0 si Clivi atiende directamente · 0.6 si parcial · 0.3 si informativo puro
 *
 * ─── USO ─────────────────────────────────────────────────────────────────────
 *
 *   import { generateKeywordBatch, scoreKeywords } from "./keyword-engine";
 *
 *   // Generar batch de 20 keywords priorizadas para glucosa y peso
 *   const batch = generateKeywordBatch({ topics: ["glucosa", "peso"], batchSize: 20 });
 *
 *   // Integrar con GSC para re-scorear con datos reales
 *   const rescored = scoreKeywords(batch, gscData);
 */

import type { KeywordInput, TopicSlug } from "./types";

// ─────────────────────────────────────────────────────────────────────────────
// TIPOS INTERNOS
// ─────────────────────────────────────────────────────────────────────────────

export interface ScoredKeyword extends KeywordInput {
	score:          number;
	cluster:        string;
	estimatedVol:   number;
	intentScore:    number;   // 1-3
	cliviRelevance: number;   // 0.3-1.0
	posZone:        number;   // 10-100
	opCTR:          number;   // 0-100
}

export interface GscRow {
	keyword:    string;
	clicks:     number;
	impressions: number;
	ctr:        number;   // decimal 0-1
	position:   number;
}

export interface KeywordEngineOptions {
	topics?:          TopicSlug[];
	batchSize?:       number;
	minScore?:        number;
	excludeSlugs?:    string[];   // slugs ya publicados para no duplicar
	gscData?:         GscRow[];   // opcional: datos reales de GSC para re-scorear
}

// ─────────────────────────────────────────────────────────────────────────────
// BASE DE KEYWORDS POR PILAR Y CLUSTER
// Anclada 100% en la oferta real de Clivi
// ─────────────────────────────────────────────────────────────────────────────

const KEYWORD_UNIVERSE: ScoredKeyword[] = [

	// ══════════════════════════════════════════════════════════════
	// PILAR: glucosa — Diabetes tipo 2, prediabetes, medicamentos
	// ══════════════════════════════════════════════════════════════

	// Cluster: medicamentos GLP-1 (alta transaccionalidad, Clivi los prescribe)
	kw("semaglutida para qué sirve", "informational", "glucosa", "article", "glp1-medicamentos", 95000, 3, 1.0),
	kw("semaglutida precio México", "transactional", "glucosa", "article", "glp1-medicamentos", 67000, 3, 1.0),
	kw("ozempic para qué sirve", "informational", "glucosa", "article", "glp1-medicamentos", 80000, 3, 1.0),
	kw("ozempic precio México", "transactional", "glucosa", "article", "glp1-medicamentos", 55000, 3, 1.0),
	kw("tirzepatida para qué sirve", "informational", "glucosa", "article", "glp1-medicamentos", 45000, 3, 1.0),
	kw("tirzepatida precio en México", "transactional", "glucosa", "article", "glp1-medicamentos", 61000, 3, 1.0),
	kw("mounjaro precio en México", "transactional", "glucosa", "article", "glp1-medicamentos", 61000, 3, 1.0),
	kw("mounjaro para qué sirve", "informational", "glucosa", "article", "glp1-medicamentos", 40000, 3, 1.0),
	kw("rybelsus para qué sirve", "informational", "glucosa", "article", "glp1-medicamentos", 28000, 3, 1.0),
	kw("ozempic vs wegovy diferencia", "informational", "glucosa", "article", "glp1-medicamentos", 22000, 2, 1.0),
	kw("semaglutida vs tirzepatida", "informational", "glucosa", "article", "glp1-medicamentos", 18000, 2, 1.0),
	kw("ozempic efectos secundarios", "informational", "glucosa", "article", "glp1-medicamentos", 35000, 2, 1.0),
	kw("mounjaro efectos secundarios", "informational", "glucosa", "article", "glp1-medicamentos", 25000, 2, 1.0),
	kw("semaglutida dosis semanal", "informational", "glucosa", "article", "glp1-medicamentos", 20000, 3, 1.0),
	kw("tirzepatida efectos secundarios", "informational", "glucosa", "article", "glp1-medicamentos", 22000, 2, 1.0),

	// Cluster: antidiabéticos orales
	kw("metformina para qué sirve", "informational", "glucosa", "article", "antidiabeticos-orales", 85000, 2, 1.0),
	kw("metformina para bajar de peso dosis", "informational", "glucosa", "article", "antidiabeticos-orales", 23000, 2, 0.8),
	kw("metformina precio en México", "transactional", "glucosa", "article", "antidiabeticos-orales", 8000, 3, 1.0),
	kw("sitagliptina para qué sirve", "informational", "glucosa", "article", "antidiabeticos-orales", 65000, 2, 1.0),
	kw("sitagliptina dosis y efectos", "informational", "glucosa", "article", "antidiabeticos-orales", 30000, 2, 1.0),
	kw("glibenclamida para qué sirve y cómo se toma", "informational", "glucosa", "article", "antidiabeticos-orales", 60000, 2, 1.0),
	kw("empagliflozina para qué sirve", "informational", "glucosa", "article", "antidiabeticos-orales", 35000, 2, 1.0),
	kw("jardiance para qué sirve", "informational", "glucosa", "article", "antidiabeticos-orales", 28000, 2, 1.0),
	kw("glipizida para qué sirve", "informational", "glucosa", "article", "antidiabeticos-orales", 18000, 2, 1.0),

	// Cluster: condición diabetes
	kw("síntomas diabetes tipo 2", "informational", "glucosa", "article", "condicion-diabetes", 45000, 1, 0.8),
	kw("cómo saber si tengo diabetes", "informational", "glucosa", "article", "condicion-diabetes", 38000, 1, 0.8),
	kw("qué es la prediabetes", "informational", "glucosa", "guide", "condicion-diabetes", 32000, 1, 0.8),
	kw("prediabetes síntomas y tratamiento", "informational", "glucosa", "guide", "condicion-diabetes", 25000, 2, 1.0),
	kw("cómo bajar la glucosa rápido", "informational", "glucosa", "article", "condicion-diabetes", 55000, 2, 0.8),
	kw("glucosa en ayunas normal rango", "informational", "glucosa", "article", "condicion-diabetes", 42000, 1, 0.8),
	kw("hemoglobina glucosilada qué es", "informational", "glucosa", "article", "condicion-diabetes", 28000, 1, 0.8),
	kw("resistencia a la insulina síntomas", "informational", "glucosa", "article", "condicion-diabetes", 35000, 2, 0.8),
	kw("resistencia a la insulina tratamiento", "informational", "glucosa", "article", "condicion-diabetes", 22000, 2, 1.0),
	kw("diabetes tipo 2 tratamiento sin medicamento", "informational", "glucosa", "guide", "condicion-diabetes", 18000, 2, 0.8),
	kw("diabetes tipo 2 tiene cura", "informational", "glucosa", "article", "condicion-diabetes", 28000, 1, 0.6),
	kw("valores normales de glucosa en sangre", "informational", "glucosa", "article", "condicion-diabetes", 40000, 1, 0.8),
	kw("síndrome metabólico síntomas", "informational", "glucosa", "article", "condicion-diabetes", 20000, 2, 0.8),
	kw("hipoglucemia síntomas qué hacer", "informational", "glucosa", "article", "condicion-diabetes", 32000, 2, 0.8),

	// Cluster: tratamiento diabetes clínico (alto potencial de conversión)
	kw("tratamiento para diabetes tipo 2 en México", "commercial", "glucosa", "guide", "tratamiento-diabetes", 30000, 3, 1.0),
	kw("clínica para diabetes en México", "commercial", "glucosa", "article", "tratamiento-diabetes", 18000, 3, 1.0),
	kw("endocrinólogo para diabetes en línea", "commercial", "glucosa", "article", "tratamiento-diabetes", 12000, 3, 1.0),
	kw("consulta médica diabetes online México", "commercial", "glucosa", "article", "tratamiento-diabetes", 10000, 3, 1.0),
	kw("cómo controlar la diabetes naturalmente", "informational", "glucosa", "article", "tratamiento-diabetes", 35000, 2, 0.6),
	kw("dieta para diabéticos tipo 2 menú semanal", "informational", "glucosa", "guide", "tratamiento-diabetes", 45000, 2, 0.8),

	// ══════════════════════════════════════════════════════════════
	// PILAR: peso — Obesidad, sobrepeso, pérdida de peso
	// ══════════════════════════════════════════════════════════════

	// Cluster: medicamentos para bajar de peso
	kw("wegovy para qué sirve", "informational", "peso", "article", "medicamentos-peso", 30000, 3, 1.0),
	kw("wegovy precio en México", "transactional", "peso", "article", "medicamentos-peso", 25000, 3, 1.0),
	kw("saxenda para qué sirve", "informational", "peso", "article", "medicamentos-peso", 28000, 3, 1.0),
	kw("saxenda precio en México", "transactional", "peso", "article", "medicamentos-peso", 20000, 3, 1.0),
	kw("inyecciones para bajar de peso en México", "commercial", "peso", "article", "medicamentos-peso", 34000, 3, 1.0),
	kw("pastillas para bajar de peso recetadas", "commercial", "peso", "article", "medicamentos-peso", 42000, 3, 0.8),
	kw("liraglutida para qué sirve", "informational", "peso", "article", "medicamentos-peso", 22000, 2, 1.0),
	kw("medicamento GLP-1 para bajar de peso", "informational", "peso", "article", "medicamentos-peso", 25000, 3, 1.0),
	kw("cuánto se pierde con wegovy en un mes", "informational", "peso", "article", "medicamentos-peso", 18000, 2, 0.8),
	kw("ozempic para bajar de peso sin diabetes", "informational", "peso", "article", "medicamentos-peso", 30000, 2, 1.0),

	// Cluster: condición obesidad / sobrepeso
	kw("obesidad mórbida tratamiento sin cirugía", "commercial", "peso", "guide", "condicion-obesidad", 18000, 3, 1.0),
	kw("índice de masa corporal normal", "informational", "peso", "article", "condicion-obesidad", 35000, 1, 0.6),
	kw("cómo calcular mi IMC", "informational", "peso", "article", "condicion-obesidad", 55000, 1, 0.6),
	kw("obesidad causas y consecuencias", "informational", "peso", "article", "condicion-obesidad", 28000, 1, 0.6),
	kw("sobrepeso vs obesidad diferencia", "informational", "peso", "article", "condicion-obesidad", 20000, 1, 0.6),
	kw("grasa visceral qué es y cómo eliminarla", "informational", "peso", "article", "condicion-obesidad", 38000, 2, 0.8),
	kw("por qué no bajo de peso aunque hago dieta", "informational", "peso", "article", "condicion-obesidad", 42000, 2, 0.8),

	// Cluster: tratamiento pérdida de peso (conversión directa)
	kw("tratamiento médico para bajar de peso en México", "commercial", "peso", "guide", "tratamiento-peso", 28000, 3, 1.0),
	kw("clínica para bajar de peso en México", "commercial", "peso", "article", "tratamiento-peso", 12000, 3, 1.0),
	kw("médico para bajar de peso en línea", "commercial", "peso", "article", "tratamiento-peso", 15000, 3, 1.0),
	kw("programa médico para bajar de peso", "commercial", "peso", "guide", "tratamiento-peso", 12000, 3, 1.0),
	kw("tratamiento para bajar de peso sin cirugía", "commercial", "peso", "article", "tratamiento-peso", 22000, 3, 1.0),
	kw("endocrinólogo para bajar de peso", "commercial", "peso", "article", "tratamiento-peso", 18000, 3, 1.0),
	kw("cómo bajar de peso con diabetes tipo 2", "informational", "peso", "article", "tratamiento-peso", 25000, 2, 1.0),
	kw("bajar de peso con medicamento recetado", "commercial", "peso", "article", "tratamiento-peso", 20000, 3, 1.0),

	// ══════════════════════════════════════════════════════════════
	// PILAR: meal-plan — Nutrición clínica
	// ══════════════════════════════════════════════════════════════

	// Cluster: alimentación para diabetes
	kw("dieta para diabéticos qué pueden comer", "informational", "meal-plan", "guide", "alimentacion-diabetes", 48000, 2, 0.8),
	kw("alimentos que suben la glucosa rápido", "informational", "meal-plan", "article", "alimentacion-diabetes", 38000, 1, 0.6),
	kw("alimentos permitidos para diabéticos", "informational", "meal-plan", "article", "alimentacion-diabetes", 42000, 1, 0.6),
	kw("índice glucémico de los alimentos tabla", "informational", "meal-plan", "article", "alimentacion-diabetes", 35000, 1, 0.6),
	kw("plan de alimentación para diabéticos", "informational", "meal-plan", "guide", "alimentacion-diabetes", 30000, 2, 0.8),
	kw("tortillas de nopal para diabetes", "informational", "meal-plan", "article", "alimentacion-diabetes", 18000, 1, 0.6),
	kw("desayuno para diabéticos recetas fáciles", "informational", "meal-plan", "article", "alimentacion-diabetes", 28000, 1, 0.6),

	// Cluster: alimentación para bajar de peso
	kw("qué comer para bajar de peso con diabetes", "informational", "meal-plan", "article", "alimentacion-peso", 32000, 2, 0.8),
	kw("dieta cetogénica y diabetes tipo 2", "informational", "meal-plan", "article", "alimentacion-peso", 25000, 2, 0.6),
	kw("plan nutricional para bajar de peso", "commercial", "meal-plan", "guide", "alimentacion-peso", 22000, 2, 0.8),
	kw("nutrióloga en línea México", "commercial", "meal-plan", "article", "alimentacion-peso", 15000, 3, 1.0),
	kw("ayuno intermitente para diabéticos es seguro", "informational", "meal-plan", "article", "alimentacion-peso", 28000, 2, 0.6),
	kw("macros para bajar de peso y controlar glucosa", "informational", "meal-plan", "article", "alimentacion-peso", 12000, 2, 0.8),

	// ══════════════════════════════════════════════════════════════
	// PILAR: journey — Estilo de vida, movimiento, hábitos
	// ══════════════════════════════════════════════════════════════

	// Cluster: ejercicio y glucosa
	kw("ejercicio para bajar la glucosa", "informational", "journey", "article", "ejercicio-glucosa", 35000, 2, 0.6),
	kw("caminar después de comer glucosa", "informational", "journey", "article", "ejercicio-glucosa", 28000, 1, 0.6),
	kw("ejercicio para diabéticos tipo 2 cuál es el mejor", "informational", "journey", "article", "ejercicio-glucosa", 22000, 2, 0.6),
	kw("cuántos pasos al día para bajar glucosa", "informational", "journey", "article", "ejercicio-glucosa", 18000, 1, 0.6),

	// Cluster: hábitos y control metabólico
	kw("cómo mejorar la sensibilidad a la insulina", "informational", "journey", "guide", "habitos-metabolicos", 20000, 2, 0.8),
	kw("sueño y diabetes relación", "informational", "journey", "article", "habitos-metabolicos", 15000, 1, 0.6),
	kw("estrés y glucosa relación", "informational", "journey", "article", "habitos-metabolicos", 18000, 1, 0.6),
	kw("hábitos para controlar la diabetes sin medicamento", "informational", "journey", "guide", "habitos-metabolicos", 22000, 2, 0.8),
	kw("cómo mantener el peso después de bajar", "informational", "journey", "article", "habitos-metabolicos", 28000, 2, 0.8),
	kw("pérdida de peso sostenible sin efecto rebote", "informational", "journey", "guide", "habitos-metabolicos", 25000, 2, 0.8),
];

// ─────────────────────────────────────────────────────────────────────────────
// FUNCIÓN AUXILIAR PARA CREAR KEYWORDS CON SCORE CALCULADO
// ─────────────────────────────────────────────────────────────────────────────

function kw(
	keyword: string,
	intent: KeywordInput["intent"],
	topic: TopicSlug,
	variant: KeywordInput["variant"],
	cluster: string,
	estimatedVol: number,
	intentLevel: 1 | 2 | 3,
	cliviRelevance: number,
	posZone = 70,
	opCTR = 85,
): ScoredKeyword {
	const volNorm      = Math.min(100, (estimatedVol / 100000) * 100);
	const intentScore  = intentLevel === 3 ? 100 : intentLevel === 2 ? 70 : 40;
	const score        = (volNorm * 0.30) + (opCTR * 0.25) + (posZone * 0.20)
	                   + (intentScore * 0.15) + (cliviRelevance * 100 * 0.10);

	const extra_tags = [cluster, topic];

	return {
		keyword,
		intent,
		topic,
		variant,
		monthly_searches: estimatedVol,
		extra_tags,
		score: Math.round(score),
		cluster,
		estimatedVol,
		intentScore: intentLevel,
		cliviRelevance,
		posZone,
		opCTR,
	};
}

// ─────────────────────────────────────────────────────────────────────────────
// FUNCIÓN PRINCIPAL: Re-scorear con datos reales de GSC
// ─────────────────────────────────────────────────────────────────────────────

export function scoreKeywords(
	keywords: ScoredKeyword[],
	gscData: GscRow[],
): ScoredKeyword[] {
	const gscMap = new Map<string, GscRow>();
	for (const row of gscData) {
		gscMap.set(row.keyword.toLowerCase().trim(), row);
	}

	return keywords.map((kw) => {
		const gsc = gscMap.get(kw.keyword.toLowerCase().trim());
		if (!gsc) return kw;

		const volNorm  = Math.min(100, (gsc.impressions / 100000) * 100);
		const opCTR    = Math.max(0, 100 - (gsc.ctr * 100));
		const posZone  = gsc.position <= 3 ? 20
		               : gsc.position <= 10 ? 100
		               : gsc.position <= 20 ? 60 : 10;
		const iScore   = kw.intentScore === 3 ? 100 : kw.intentScore === 2 ? 70 : 40;

		const score = (volNorm * 0.30) + (opCTR * 0.25) + (posZone * 0.20)
		            + (iScore * 0.15) + (kw.cliviRelevance * 100 * 0.10);

		return {
			...kw,
			monthly_searches: gsc.impressions,
			estimatedVol:     gsc.impressions,
			opCTR,
			posZone,
			score: Math.round(score),
		};
	});
}

// ─────────────────────────────────────────────────────────────────────────────
// FUNCIÓN PRINCIPAL: Generar batch priorizado
// ─────────────────────────────────────────────────────────────────────────────

export function generateKeywordBatch(opts: KeywordEngineOptions = {}): KeywordInput[] {
	const {
		topics,
		batchSize   = 10,
		minScore    = 0,
		excludeSlugs = [],
		gscData,
	} = opts;

	let pool = [...KEYWORD_UNIVERSE];

	// Filtrar por topics si se especifican
	if (topics && topics.length > 0) {
		pool = pool.filter((k) => topics.includes(k.topic));
	}

	// Re-scorear con GSC si está disponible
	if (gscData && gscData.length > 0) {
		pool = scoreKeywords(pool, gscData);
	}

	// Excluir slugs ya publicados
	if (excludeSlugs.length > 0) {
		pool = pool.filter((k) => {
			const slug = k.keyword.toLowerCase()
				.normalize("NFD").replace(/[\u0300-\u036f]/g, "")
				.replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
			return !excludeSlugs.includes(slug);
		});
	}

	// Filtrar por score mínimo
	pool = pool.filter((k) => k.score >= minScore);

	// Ordenar por score pero con aleatoriedad dentro de cada tercio
	// Así cada run genera artículos diferentes en lugar de siempre los mismos
	pool.sort((a, b) => b.score - a.score);
	const third = Math.ceil(pool.length / 3);
	const shuffled = [
		...pool.slice(0, third).sort(() => Math.random() - 0.5),
		...pool.slice(third, third * 2).sort(() => Math.random() - 0.5),
		...pool.slice(third * 2).sort(() => Math.random() - 0.5),
	];
	pool = shuffled;

	// Diversificar: máximo 3 keywords del mismo cluster en un batch
	const clusterCount = new Map<string, number>();
	const selected: ScoredKeyword[] = [];

	for (const k of pool) {
		if (selected.length >= batchSize) break;
		const count = clusterCount.get(k.cluster) ?? 0;
		if (count >= 3) continue;
		clusterCount.set(k.cluster, count + 1);
		selected.push(k);
	}

	// Convertir a KeywordInput (sin campos de scoring internos)
	return selected.map(({ keyword, intent, topic, variant, monthly_searches, extra_tags }) => ({
		keyword,
		intent,
		topic,
		variant,
		monthly_searches,
		extra_tags,
	}));
}

// ─────────────────────────────────────────────────────────────────────────────
// EXPORTAR UNIVERSO COMPLETO (para auditoría o análisis)
// ─────────────────────────────────────────────────────────────────────────────

export function getFullUniverse(): ScoredKeyword[] {
	return [...KEYWORD_UNIVERSE].sort((a, b) => b.score - a.score);
}

export function getByCluster(cluster: string): ScoredKeyword[] {
	return KEYWORD_UNIVERSE.filter((k) => k.cluster === cluster)
		.sort((a, b) => b.score - a.score);
}

export function getTopByTopic(topic: TopicSlug, n = 5): ScoredKeyword[] {
	return KEYWORD_UNIVERSE.filter((k) => k.topic === topic)
		.sort((a, b) => b.score - a.score)
		.slice(0, n);
}
