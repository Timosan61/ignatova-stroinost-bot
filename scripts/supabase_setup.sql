-- ========================================
-- Supabase Vector Store Setup
-- ========================================
--
-- Этот скрипт создает таблицу и функции для работы с
-- векторным поиском через pgvector extension.
--
-- ИНСТРУКЦИЯ:
-- 1. Открой Supabase Dashboard → SQL Editor
-- 2. Создай новый query
-- 3. Скопируй весь этот файл и выполни
-- 4. Проверь что таблица course_knowledge создана
--
-- ========================================

-- Enable pgvector extension (если еще не включен)
CREATE EXTENSION IF NOT EXISTS vector;

-- ========================================
-- Таблица для knowledge entities
-- ========================================

CREATE TABLE IF NOT EXISTS course_knowledge (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding VECTOR(1536),  -- OpenAI text-embedding-3-small
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- Индексы для оптимизации
-- ========================================

-- Index для similarity search (ivfflat algorithm)
-- lists = 100 оптимален для ~3-10K vectors
CREATE INDEX IF NOT EXISTS idx_course_knowledge_embedding
ON course_knowledge
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Index для entity_type фильтрации
CREATE INDEX IF NOT EXISTS idx_course_knowledge_entity_type
ON course_knowledge(entity_type);

-- Index для timestamp сортировки
CREATE INDEX IF NOT EXISTS idx_course_knowledge_created_at
ON course_knowledge(created_at DESC);

-- ========================================
-- RPC Function для similarity search
-- ========================================

CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 5,
    filter_entity_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    id TEXT,
    entity_type TEXT,
    title TEXT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        course_knowledge.id,
        course_knowledge.entity_type,
        course_knowledge.title,
        course_knowledge.content,
        course_knowledge.metadata,
        1 - (course_knowledge.embedding <=> query_embedding) AS similarity
    FROM course_knowledge
    WHERE
        (filter_entity_type IS NULL OR course_knowledge.entity_type = filter_entity_type)
        AND (1 - (course_knowledge.embedding <=> query_embedding)) > match_threshold
    ORDER BY course_knowledge.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ========================================
-- RPC Function для статистики
-- ========================================

CREATE OR REPLACE FUNCTION get_knowledge_stats()
RETURNS TABLE (
    entity_type TEXT,
    count BIGINT,
    avg_content_length FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        course_knowledge.entity_type,
        COUNT(*) AS count,
        AVG(LENGTH(course_knowledge.content)) AS avg_content_length
    FROM course_knowledge
    GROUP BY course_knowledge.entity_type
    ORDER BY count DESC;
END;
$$;

-- ========================================
-- Trigger для обновления updated_at
-- ========================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_course_knowledge_updated_at
    BEFORE UPDATE ON course_knowledge
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- Row Level Security (RLS) policies
-- ========================================

-- Включить RLS для таблицы
ALTER TABLE course_knowledge ENABLE ROW LEVEL SECURITY;

-- Policy для service_role: полный доступ
CREATE POLICY "Service role has full access"
    ON course_knowledge
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Policy для anon/authenticated: только чтение
CREATE POLICY "Public read access"
    ON course_knowledge
    FOR SELECT
    TO anon, authenticated
    USING (true);

-- ========================================
-- Готово!
-- ========================================

-- Проверка что всё создано
SELECT
    'Setup complete!' as message,
    COUNT(*) as total_entities
FROM course_knowledge;

-- Проверка что индексы созданы
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'course_knowledge';
