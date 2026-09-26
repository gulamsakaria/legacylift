-- LegacyLift demo: Legacy School Portal database schema + seed data.
-- Includes Bangla (UTF-8) content to verify the modernization pipeline
-- never mangles non-Latin text.

CREATE DATABASE IF NOT EXISTS legacy_school_portal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE legacy_school_portal;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(128) NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    class VARCHAR(32) NOT NULL,
    guardian_phone VARCHAR(32),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE news (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    tags VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE contact_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    message TEXT NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    uploaded_by INT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Seed data (password hashes are md5('password123') for demo login testing)
INSERT INTO admins (username, password) VALUES ('admin', MD5('admin123'));
INSERT INTO users (username, email, password) VALUES
    ('rahim.k', 'rahim.k@example.com', MD5('password123')),
    ('nusrat.j', 'nusrat.j@example.com', MD5('password123'));

INSERT INTO students (name, class, guardian_phone) VALUES
    ('রহিম উদ্দিন', 'Class 8', '01711000001'),
    ('নুসরাত জাহান', 'Class 9', '01711000002'),
    ('করিম শেখ', 'Class 7', '01711000003'),
    ('ফাতেমা বেগম', 'Class 10', '01711000004');

INSERT INTO news (title, body, tags, created_at) VALUES
    ('বার্ষিক ক্রীড়া প্রতিযোগিতা আগামী সপ্তাহে', 'আগামী সোমবার থেকে স্কুলের বার্ষিক ক্রীড়া প্রতিযোগিতা শুরু হচ্ছে। সকল শিক্ষার্থীকে অংশগ্রহণের জন্য অনুরোধ করা হলো।', 'sports,annual,notice', NOW()),
    ('Half-yearly exam routine published', 'The half-yearly examination routine for all classes has been published on the notice board. Please check your respective class schedule.', 'exam,routine', NOW()),
    ('বৃত্তি পরীক্ষার ফলাফল প্রকাশিত', 'এই বছরের বৃত্তি পরীক্ষার ফলাফল প্রকাশ করা হয়েছে। সফল শিক্ষার্থীদের অভিনন্দন।', 'result,scholarship', NOW());
