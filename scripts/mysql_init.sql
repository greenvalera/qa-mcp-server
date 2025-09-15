-- New MySQL schema for QA Checklists structure
-- This schema supports hierarchical QA structure with sections, checklists, and testcases

USE qa;

-- Drop existing tables (careful - this will delete data)
DROP TABLE IF EXISTS doc_features;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS features;

-- Create qa_sections table (root sections like "Checklist WEB", "Checklist MOB")
CREATE TABLE IF NOT EXISTS qa_sections (
  id INT AUTO_INCREMENT PRIMARY KEY,
  confluence_page_id VARCHAR(64) NOT NULL UNIQUE,
  title VARCHAR(512) NOT NULL,
  description TEXT NULL,
  url VARCHAR(1024) NOT NULL,
  space_key VARCHAR(64) NOT NULL,
  parent_section_id INT NULL, -- for hierarchical structure
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  INDEX idx_qa_sections_confluence_id (confluence_page_id),
  INDEX idx_qa_sections_space (space_key),
  INDEX idx_qa_sections_parent (parent_section_id),
  FOREIGN KEY (parent_section_id) REFERENCES qa_sections(id) ON DELETE CASCADE
);

-- Create checklists table (pages with testcases like "WEB: Billing History")
CREATE TABLE IF NOT EXISTS checklists (
  id INT AUTO_INCREMENT PRIMARY KEY,
  confluence_page_id VARCHAR(64) NOT NULL UNIQUE,
  title VARCHAR(512) NOT NULL,
  description TEXT NULL,
  additional_content TEXT NULL, -- Additional information before testcases table
  url VARCHAR(1024) NOT NULL,
  space_key VARCHAR(64) NOT NULL,
  section_id INT NOT NULL, -- belongs to a QA section
  content_hash CHAR(64) NOT NULL,
  version INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  INDEX idx_checklists_confluence_id (confluence_page_id),
  INDEX idx_checklists_section (section_id),
  INDEX idx_checklists_space (space_key),
  INDEX idx_checklists_hash (content_hash),
  FOREIGN KEY (section_id) REFERENCES qa_sections(id) ON DELETE CASCADE
);

-- Create configs table (separate entities referenced by testcases)
CREATE TABLE IF NOT EXISTS configs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  url VARCHAR(1024) NULL,
  description TEXT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  INDEX idx_configs_name (name)
);

-- Create testcases table (atomic test elements)
CREATE TABLE IF NOT EXISTS testcases (
  id INT AUTO_INCREMENT PRIMARY KEY,
  checklist_id INT NOT NULL,
  step TEXT NOT NULL, -- STEP field
  expected_result TEXT NOT NULL, -- EXPECTED RESULT field
  screenshot VARCHAR(1024) NULL, -- SCREENSHOT field
  priority ENUM('LOWEST', 'LOW', 'MEDIUM', 'HIGH', 'HIGHEST', 'CRITICAL') NULL, -- PRIORITY field
  test_group ENUM('GENERAL', 'CUSTOM') NULL, -- Main test group (GENERAL or CUSTOM)
  functionality VARCHAR(255) NULL, -- Functionality group within test_group
  subcategory VARCHAR(255) NULL, -- Subcategory from parent page hierarchy
  order_index INT NOT NULL DEFAULT 0, -- Order within checklist
  config_id INT NULL, -- Reference to config
  qa_auto_coverage VARCHAR(255) NULL, -- QA AUTO COVERAGE field
  embedding LONGTEXT NULL, -- Vector embedding for semantic search
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  INDEX idx_testcases_checklist (checklist_id),
  INDEX idx_testcases_test_group (test_group),
  INDEX idx_testcases_functionality (functionality),
  INDEX idx_testcases_subcategory (subcategory),
  INDEX idx_testcases_priority (priority),
  INDEX idx_testcases_config (config_id),
  INDEX idx_testcases_order (checklist_id, order_index),
  FOREIGN KEY (checklist_id) REFERENCES checklists(id) ON DELETE CASCADE,
  FOREIGN KEY (config_id) REFERENCES configs(id) ON DELETE SET NULL
);

-- Create checklist_configs table (many-to-many relationship for configs mentioned in checklist)
CREATE TABLE IF NOT EXISTS checklist_configs (
  checklist_id INT NOT NULL,
  config_id INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  PRIMARY KEY (checklist_id, config_id),
  FOREIGN KEY (checklist_id) REFERENCES checklists(id) ON DELETE CASCADE,
  FOREIGN KEY (config_id) REFERENCES configs(id) ON DELETE CASCADE
);

-- Keep ingestion_jobs table as is (for tracking data loads)
-- CREATE TABLE ingestion_jobs - already exists

-- Insert sample data for testing

-- Sample QA Sections
INSERT IGNORE INTO qa_sections (confluence_page_id, title, description, url, space_key) VALUES 
('43624449', 'Checklist WEB', 'Web application testing checklists', 'https://confluence.togethernetworks.com/pages/43624449', 'QMT'),
('117706559', 'Checklist MOB', 'Mobile application testing checklists', 'https://confluence.togethernetworks.com/pages/117706559', 'QMT'),
('340830206', 'Payment Page', 'Payment functionality testing', 'https://confluence.togethernetworks.com/pages/340830206', 'QMT');

-- Sample Configs
INSERT IGNORE INTO configs (name, url, description) VALUES 
('billingHistoryConfig', 'https://my.platformphoenix.com/search/showConfigs?fileName=%2Fbilling%2Fhistory.yaml', 'Billing history configuration'),
('paymentConfig', 'https://my.platformphoenix.com/search/showConfigs?fileName=%2Fpayment%2Fconfig.yaml', 'Payment processing configuration'),
('authConfig', 'https://my.platformphoenix.com/search/showConfigs?fileName=%2Fauth%2Fconfig.yaml', 'Authentication configuration');

-- Sample Checklists
INSERT IGNORE INTO checklists (confluence_page_id, title, description, url, space_key, section_id, content_hash, version) VALUES 
('billing_history_123', 'WEB: Billing History', 'Testing billing history functionality', 'https://confluence.togethernetworks.com/pages/billing_history_123', 'QMT', 1, SHA2('billing history content', 256), 1),
('search_456', 'WEB: Search', 'Testing search functionality', 'https://confluence.togethernetworks.com/pages/search_456', 'QMT', 1, SHA2('search content', 256), 1);

-- Sample Testcases
INSERT IGNORE INTO testcases (checklist_id, step, expected_result, test_group, functionality, priority, order_index, config_id) VALUES 
-- Billing History testcases
(1, 'Navigate to billing history page', 'Billing history page loads successfully', 'GENERAL', 'Navigation', 'HIGH', 1, 1),
(1, 'Verify billing history table displays', 'Table shows all user transactions', 'GENERAL', 'Display', 'HIGH', 2, 1),
(1, 'Test pagination controls', 'Pagination works correctly', 'GENERAL', 'Pagination', 'MEDIUM', 3, NULL),
(1, 'Test custom date filter', 'Filter shows transactions for selected period', 'CUSTOM', 'Filtering', 'MEDIUM', 4, 1),

-- Search testcases  
(2, 'Enter search query', 'Search results are displayed', 'GENERAL', 'Basic Search', 'HIGH', 1, NULL),
(2, 'Test advanced search filters', 'Filters apply correctly to results', 'GENERAL', 'Advanced Search', 'HIGH', 2, NULL),
(2, 'Test search with special characters', 'Special characters are handled properly', 'CUSTOM', 'Edge Cases', 'LOW', 3, NULL);

-- Link checklists to configs
INSERT IGNORE INTO checklist_configs (checklist_id, config_id) VALUES 
(1, 1), -- Billing History uses billingHistoryConfig
(1, 2), -- Billing History also uses paymentConfig
(2, 3); -- Search uses authConfig

-- Create indexes for better performance
-- Note: Full-text search indexes on TEXT columns need special handling in MySQL
-- Can be added later with: CREATE FULLTEXT INDEX idx_testcases_fulltext ON testcases(step, expected_result);

-- Additional indexes are already created in the table definitions above
-- Uncomment the following lines if you need to create additional indexes:
-- CREATE INDEX idx_checklists_title ON checklists(title);
-- CREATE INDEX idx_qa_sections_title ON qa_sections(title);

-- Create a view for easy querying of complete testcase information
CREATE OR REPLACE VIEW testcase_details AS
SELECT 
    t.id as testcase_id,
    t.step,
    t.expected_result,
    t.screenshot,
    t.priority,
    t.functionality,
    t.subcategory,
    t.order_index,
    t.qa_auto_coverage,
    c.title as checklist_title,
    c.confluence_page_id as checklist_page_id,
    c.url as checklist_url,
    s.title as section_title,
    s.confluence_page_id as section_page_id,
    cfg.name as config_name,
    cfg.url as config_url,
    cfg.description as config_description
FROM testcases t
JOIN checklists c ON t.checklist_id = c.id
JOIN qa_sections s ON c.section_id = s.id
LEFT JOIN configs cfg ON t.config_id = cfg.id
ORDER BY s.title, c.title, t.order_index;
