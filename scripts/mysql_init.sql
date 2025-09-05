-- MySQL initialization script for QA MCP Server
-- This script creates the database schema according to the specification

USE qa;

-- Create features table
CREATE TABLE IF NOT EXISTS features (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  description TEXT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  INDEX idx_features_name (name),
  INDEX idx_features_created (created_at)
);

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  confluence_page_id VARCHAR(64) NOT NULL,
  title VARCHAR(512) NOT NULL,
  url VARCHAR(1024) NOT NULL,
  space_key VARCHAR(64) NOT NULL,
  labels JSON NULL,
  content_hash CHAR(64) NOT NULL,
  version INT NULL,
  updated_at TIMESTAMP NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE KEY uk_documents_page_id (confluence_page_id),
  INDEX idx_documents_space (space_key),
  INDEX idx_documents_updated (updated_at),
  INDEX idx_documents_hash (content_hash),
  INDEX idx_documents_space_updated (space_key, updated_at)
);

-- Create document-feature association table
CREATE TABLE IF NOT EXISTS doc_features (
  document_id INT NOT NULL,
  feature_id INT NOT NULL,
  confidence FLOAT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  PRIMARY KEY (document_id, feature_id),
  FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
  FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE CASCADE,
  
  INDEX idx_doc_features_document (document_id),
  INDEX idx_doc_features_feature (feature_id),
  INDEX idx_doc_features_confidence (confidence)
);

-- Create ingestion jobs table
CREATE TABLE IF NOT EXISTS ingestion_jobs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  finished_at TIMESTAMP NULL,
  status ENUM('running','success','failed') NOT NULL DEFAULT 'running',
  details TEXT NULL,
  documents_processed INT DEFAULT 0,
  chunks_created INT DEFAULT 0,
  features_created INT DEFAULT 0,
  
  INDEX idx_ingestion_status (status),
  INDEX idx_ingestion_started (started_at)
);

-- Insert some sample features for testing
INSERT IGNORE INTO features (name, description) VALUES 
('Authentication', 'User authentication, login, logout, session management, MFA'),
('Authorization', 'User permissions, roles, access control, security policies'),
('User Interface', 'Frontend components, forms, navigation, user experience'),
('API', 'REST endpoints, GraphQL, API documentation, integrations'),
('Database', 'Data models, migrations, queries, performance optimization'),
('Testing', 'Unit tests, integration tests, test automation, QA procedures'),
('Deployment', 'CI/CD, infrastructure, monitoring, production deployment'),
('Documentation', 'Technical documentation, user guides, API documentation');

-- Create a test document
INSERT IGNORE INTO documents (
  confluence_page_id, 
  title, 
  url, 
  space_key, 
  labels, 
  content_hash, 
  version,
  updated_at
) VALUES (
  'test-page-123',
  'Sample QA Checklist',
  'https://example.atlassian.net/wiki/spaces/QA/pages/123456789/Sample+QA+Checklist',
  'QA',
  JSON_ARRAY('checklist', 'qa', 'testing'),
  SHA2('Sample document content for testing purposes', 256),
  1,
  NOW()
);

-- Associate test document with testing feature
INSERT IGNORE INTO doc_features (document_id, feature_id, confidence)
SELECT d.id, f.id, 0.95
FROM documents d, features f 
WHERE d.confluence_page_id = 'test-page-123' 
  AND f.name = 'Testing';

-- Create a successful ingestion job record
INSERT INTO ingestion_jobs (
  finished_at,
  status,
  details,
  documents_processed,
  chunks_created,
  features_created
) VALUES (
  NOW(),
  'success',
  'Initial database setup with sample data',
  1,
  5,
  8
);
