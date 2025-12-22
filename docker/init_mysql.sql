-- OITELUシステム用MySQLデータベース初期化スクリプト

-- データベースが存在しない場合は作成（docker-entrypointで自動作成されるが念のため）
CREATE DATABASE IF NOT EXISTS oiteru CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE oiteru;

-- usersテーブル
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    card_id VARCHAR(255) UNIQUE NOT NULL,
    allow TINYINT(1) DEFAULT 1,
    entry VARCHAR(50),
    stock INT DEFAULT 2,
    today INT DEFAULT 0,
    total INT DEFAULT 0,
    last1 VARCHAR(50),
    last2 VARCHAR(50),
    last3 VARCHAR(50),
    last4 VARCHAR(50),
    last5 VARCHAR(50),
    last6 VARCHAR(50),
    last7 VARCHAR(50),
    last8 VARCHAR(50),
    last9 VARCHAR(50),
    last10 VARCHAR(50),
    INDEX idx_card_id (card_id),
    INDEX idx_allow (allow)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- unitsテーブル（子機情報）
CREATE TABLE IF NOT EXISTS units (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    stock INT DEFAULT 100,
    connect TINYINT(1) DEFAULT 0,
    available TINYINT(1) DEFAULT 1,
    last_seen VARCHAR(50),
    last_heartbeat DATETIME,
    ip_address VARCHAR(50),
    INDEX idx_name (name),
    INDEX idx_available (available)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- historyテーブル（操作履歴）
CREATE TABLE IF NOT EXISTS history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    txt TEXT NOT NULL,
    type VARCHAR(20) DEFAULT 'usage',  -- 'usage'=利用履歴, 'system'=システムログ, 'heartbeat'=ハートビート
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created_at (created_at),
    INDEX idx_type (type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- infoテーブル（システム情報）
CREATE TABLE IF NOT EXISTS info (
    id INT PRIMARY KEY DEFAULT 1,
    pass VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- デフォルトの管理者パスワードを設定（SHA256ハッシュ: "admin"）
-- 実運用時は必ず変更してください
INSERT INTO info (id, pass) VALUES (1, '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918')
ON DUPLICATE KEY UPDATE pass = VALUES(pass);

-- インデックスの最適化
OPTIMIZE TABLE users;
OPTIMIZE TABLE units;
OPTIMIZE TABLE history;
OPTIMIZE TABLE info;

-- 確認用
SELECT 'Database initialized successfully' AS status;
