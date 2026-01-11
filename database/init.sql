-- Database initialization script for OCR Activity Categories
-- This script creates the schema and seeds data for activity categorization

-- Create activity categories table
CREATE TABLE activity_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    calculation_type VARCHAR(50) NOT NULL, -- 'fixed_per_semester', 'fixed_per_activity', 'ratio_hours', 'ratio_days', 'ratio_pages'
    hours_awarded INTEGER, -- Hours awarded per unit (for fixed calculations)
    input_unit VARCHAR(50), -- What unit is being measured: 'hours', 'days', 'pages', 'activities', 'semesters'
    input_quantity INTEGER, -- How many input units are needed (e.g., 4 hours, 1 day, 10 pages)
    output_hours INTEGER, -- How many hours are awarded for that input quantity
    max_total_hours INTEGER, -- Maximum hours student can have in this category
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create students table
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    enrollment_number VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(500) NOT NULL,
    email VARCHAR(255),
    total_approved_hours INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create certificate submissions table for async processing
CREATE TABLE certificate_submissions (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(id),
    original_filename VARCHAR(500),
    s3_key VARCHAR(1000) NOT NULL, -- S3 object key
    file_checksum VARCHAR(64) NOT NULL, -- SHA-256 hash
    file_size BIGINT,
    mime_type VARCHAR(100),
    status VARCHAR(50) DEFAULT 'uploaded', -- 'uploaded', 'queued', 'ocr_processing', 'ocr_completed', 'metadata_extracting', 'metadata_extracted', 'categorizing', 'categorized', 'completed', 'failed'
    error_message VARCHAR(1000),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_started_at TIMESTAMP,
    processing_completed_at TIMESTAMP,
    rejected_at TIMESTAMP,
    rejection_reason VARCHAR(1000),
    rejected_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Composite unique constraint: same student cannot submit same file twice
    CONSTRAINT unique_student_file UNIQUE (student_id, file_checksum)
);

-- Create OCR texts table for audit
CREATE TABLE certificate_ocr_texts (
    id SERIAL PRIMARY KEY,
    submission_id INTEGER REFERENCES certificate_submissions(id),
    raw_text TEXT NOT NULL,
    ocr_confidence DECIMAL(5,2), -- OCR confidence score
    processing_time_ms INTEGER,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create certificate metadata table for extracted information
CREATE TABLE certificate_metadata (
    id SERIAL PRIMARY KEY,
    submission_id INTEGER REFERENCES certificate_submissions(id),
    participant_name VARCHAR(500),
    event_name VARCHAR(1000),
    location VARCHAR(500),
    event_date VARCHAR(200),
    original_hours VARCHAR(100),
    numeric_hours INTEGER,
    processing_time_ms INTEGER,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create extracted activities table to store processing results
CREATE TABLE extracted_activities (
    id SERIAL PRIMARY KEY,
    submission_id INTEGER REFERENCES certificate_submissions(id),
    metadata_id INTEGER REFERENCES certificate_metadata(id),
    student_id INTEGER REFERENCES students(id),
    category_id INTEGER REFERENCES activity_categories(id),
    calculated_hours INTEGER,
    llm_reasoning TEXT, -- Store LLM's reasoning for category selection
    
    -- Review workflow fields
    review_status VARCHAR(50) DEFAULT 'pending_review', -- 'pending_review', 'approved', 'rejected', 'manual_override'
    coordinator_id VARCHAR(100), -- ID of coordinator who reviewed
    coordinator_comments TEXT,
    reviewed_at TIMESTAMP,
    
    -- Manual override fields (when coordinator disagrees with LLM)
    override_category_id INTEGER REFERENCES activity_categories(id),
    override_hours INTEGER,
    override_reasoning TEXT,
    
    -- Final approved values (either LLM or override)
    final_category_id INTEGER REFERENCES activity_categories(id),
    final_hours INTEGER,
    
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Create indexes for better performance
CREATE INDEX idx_extracted_activities_category ON extracted_activities(category_id);
CREATE INDEX idx_extracted_activities_processed_at ON extracted_activities(processed_at);
CREATE INDEX idx_extracted_activities_review_status ON extracted_activities(review_status);
CREATE INDEX idx_extracted_activities_student ON extracted_activities(student_id);
CREATE INDEX idx_extracted_activities_submission ON extracted_activities(submission_id);
CREATE INDEX idx_certificate_submissions_checksum ON certificate_submissions(file_checksum);
CREATE INDEX idx_certificate_submissions_student_checksum ON certificate_submissions(student_id, file_checksum);
CREATE INDEX idx_certificate_submissions_status ON certificate_submissions(status);
CREATE INDEX idx_certificate_submissions_student ON certificate_submissions(student_id);
CREATE INDEX idx_students_enrollment ON students(enrollment_number);
CREATE INDEX idx_certificate_ocr_texts_submission ON certificate_ocr_texts(submission_id);
CREATE INDEX idx_certificate_metadata_submission ON certificate_metadata(submission_id);

-- Seed data with correct activity categories
INSERT INTO activity_categories (name, description, calculation_type, hours_awarded, input_unit, input_quantity, output_hours, max_total_hours) VALUES

-- Programa de iniciação científica ou tecnológica: 40h a cada período letivo, max 80h
('Programa de iniciação científica ou tecnológica', 'Atividades de iniciação científica ou tecnológica', 'fixed_per_semester', 40, 'semesters', 1, 40, 80),

-- Programa de iniciação a docência: 40h a cada período letivo, max 80h  
('Programa de iniciação a docência', 'Atividades de iniciação à docência', 'fixed_per_semester', 40, 'semesters', 1, 40, 80),

-- Programa de monitoria: 40h para cada disciplina como monitor, max 80h
('Programa de monitoria', 'Atividades de monitoria acadêmica', 'fixed_per_activity', 40, 'activities', 1, 40, 80),

-- Projeto de pesquisa ou extensão: 30h por projeto por período letivo, max 60h
('Projeto de pesquisa ou extensão', 'Participação em projetos de pesquisa ou extensão', 'fixed_per_activity', 30, 'activities', 1, 30, 60),

-- Atividades artístico-culturais e/ou esportivas: 1h para cada 2h de atividade, max 60h
('Atividades artístico-culturais e/ou esportivas', 'Teatro, música, dança, esportes, etc.', 'ratio_hours', NULL, 'hours', 2, 1, 60),

-- Curso de línguas: 1h para cada 4h de curso, max 60h
('Curso de línguas', 'Cursos de línguas estrangeiras', 'ratio_hours', NULL, 'hours', 4, 1, 60),

-- Curso na área de engenharia de computação: 1h para cada 4h de curso, max 60h
('Curso na área de engenharia de computação', 'Cursos relacionados à área de formação', 'ratio_hours', NULL, 'hours', 4, 1, 60),

-- Curso fora da área de engenharia de computação: 1h para cada 6h de curso, max 40h
('Curso fora da área de engenharia de computação', 'Cursos em áreas não relacionadas à engenharia de computação', 'ratio_hours', NULL, 'hours', 6, 1, 40),

-- Ministrar curso na área de engenharia da computação: 2h para cada 1h de curso, max 60h
('Ministrar curso na área de engenharia da computação', 'Atividades de ensino em cursos da área', 'ratio_hours', NULL, 'hours', 1, 2, 60),

-- Certificação técnica: 30h para cada certificação, max 60h
('Certificação técnica', 'Certificações técnicas profissionais', 'fixed_per_activity', 30, 'activities', 1, 30, 60),

-- Organização de eventos técnicos e/ou científicos na área do curso: 20h por evento, max 40h
('Organização de eventos técnicos e/ou científicos na área do curso', 'Comissão organizadora de eventos', 'fixed_per_activity', 20, 'activities', 1, 20, 40),

-- Participação em eventos técnicos e/ou científicos na área do curso: 4h por dia de evento, max 40h
('Participação em eventos técnicos e/ou científicos na área do curso', 'Congressos, simpósios, workshops', 'ratio_days', NULL, 'days', 1, 4, 40),

-- Participação como ouvinte em palestras relacionadas com a área do curso: 2h por palestra, max 30h
('Participação como ouvinte em palestras relacionadas com a área do curso', 'Palestras, seminários como ouvinte', 'fixed_per_activity', 2, 'activities', 1, 2, 30),

-- Participação como palestrante em palestras relacionadas com a área do curso: 8h por palestra, max 30h
('Participação como palestrante em palestras relacionadas com a área do curso', 'Ministrar palestras, seminários', 'fixed_per_activity', 8, 'activities', 1, 8, 30),

-- Projeto Social extra-curricular: 15h por projeto, max 30h
('Projeto Social extra-curricular', 'Projetos de responsabilidade social', 'fixed_per_activity', 15, 'activities', 1, 15, 30),

-- Produção técnica com relatório: 3h para cada 10 páginas, max 30h
('Produção técnica com relatório', 'Relatórios técnicos, documentação', 'ratio_pages', NULL, 'pages', 10, 3, 30);
