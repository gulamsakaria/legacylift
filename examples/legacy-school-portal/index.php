<?php
require_once __DIR__ . '/includes/bootstrap.php';

$result = mysql_query("SELECT id, title, body, created_at FROM news ORDER BY created_at DESC LIMIT 10");
$news_items = array();
while ($row = mysql_fetch_assoc($result)) {
    $news_items[] = $row;
}

$notice_count = mysql_num_rows($result);
?>
<!DOCTYPE html>
<html>
<head><title>School Portal - Home</title></head>
<body>
  <h1>Welcome to the School Portal</h1>
  <?php if (isset($_GET['welcome'])) { ?>
  <p>Welcome back, <?= $_GET['welcome'] ?>!</p>
  <?php } ?>

  <h2>Latest News (<?= $notice_count ?>)</h2>
  <?php foreach ($news_items as $item) { include __DIR__ . '/templates/news_card.phtml'; } ?>

  <p><a href="search.php">Search students</a> | <a href="student_list.php">Student list</a> | <a href="contact.php">Contact us</a></p>
</body>
</html>
