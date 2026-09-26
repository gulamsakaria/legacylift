<?php
require_once __DIR__ . '/../includes/bootstrap.php';

if (!isset($_SESSION['admin_id'])) {
    header("Location: login.php");
    exit;
}

$student_count_result = mysql_query("SELECT COUNT(*) as cnt FROM students");
$student_count = mysql_fetch_assoc($student_count_result);

$news_count_result = mysql_query("SELECT COUNT(*) as cnt FROM news");
$news_count = mysql_fetch_assoc($news_count_result);
?>
<!DOCTYPE html>
<html>
<head><title>Admin Dashboard - School Portal</title></head>
<body>
<h1>Welcome, <?= $_SESSION['admin_name'] ?></h1>
<ul>
  <li>Students: <?= $student_count['cnt'] ?></li>
  <li>News articles: <?= $news_count['cnt'] ?></li>
</ul>
<p><a href="manage_news.php">Manage News</a> | <a href="../student_list.php">Manage Students</a></p>
</body>
</html>
