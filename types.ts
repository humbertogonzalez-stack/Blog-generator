export type TopicSlug =
	| "peso" | "glucosa" | "meal-plan" | "journey"
	| "cintura" | "pulse" | "citas" | "body-scan";

export type ArticleVariant = "article" | "guide" | "story";

export interface KeywordInput {
	keyword: string;
	intent: "informational" | "commercial" | "transactional";
	topic: TopicSlug;
	variant?: ArticleVariant;
	monthly_searches?: number;
	extra_tags?: string[];
}

export interface GeneratedArticle {
	title: string;
	seoTitle: string;
	metaDescription: string;
	slug: string;
	bodyMarkdown: string;
	wordCount: number;
	tags: string[];
	imageAlt: string;
	keyTakeaways: string[];
	evidenceNote: string | null;
	references: Array<{
		authors: string;
		title: string;
		source: string;
		year: number;
		url?: string;
	}>;
	glossary: Record<string, string>;
}

export interface LinearIssueResult {
	id: string;
	identifier: string;
	url: string;
}

export interface SeoJobResult {
	keyword: string;
	status: "success" | "error";
	linearIdentifier?: string;
	linearUrl?: string;
	articleTitle?: string;
	wordCount?: number;
	error?: string;
}

export interface WorkerEnv {
	ANTHROPIC_API_KEY: string;
	LINEAR_API_KEY: string;
	LINEAR_TEAM_ID: string;
	LINEAR_TRIGGER_SECRET: string;
	BLOG_ENV: "staging" | "production";
	EMDASH_API_KEY: string;
	EMDASH_BASE_URL: string;
	KEYWORDS_KV: KVNamespace;
}
