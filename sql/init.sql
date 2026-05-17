CREATE DATABASE IF NOT EXISTS fund DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE fund;

CREATE TABLE IF NOT EXISTS fund_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS funds (
    code VARCHAR(6) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category_id INT,
    FOREIGN KEY (category_id) REFERENCES fund_categories(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fund_nav (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fund_code VARCHAR(6) NOT NULL,
    nav_date DATE NOT NULL,
    nav DECIMAL(10,4) NOT NULL,
    acc_nav DECIMAL(10,4) NOT NULL,
    FOREIGN KEY (fund_code) REFERENCES funds(code),
    UNIQUE KEY uk_fund_date (fund_code, nav_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fund_weekly (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fund_code VARCHAR(6) NOT NULL,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    change_pct DECIMAL(8,4) NOT NULL,
    FOREIGN KEY (fund_code) REFERENCES funds(code),
    UNIQUE KEY uk_fund_week (fund_code, week_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;