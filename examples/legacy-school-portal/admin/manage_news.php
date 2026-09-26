<?php
require_once __DIR__ . '/../includes/bootstrap.php';
require_once __DIR__ . '/../includes/functions.php';

if (!isset($_SESSION['admin_id'])) {
    header("Location: login.php");
    exit;
}

$logger = new legacy_logger(__DIR__ . '/../logs/news_activity.log');

if ($_SERVER['REQUEST_METHOD'] == 'POST' && isset($_POST['action']) && $_POST['action'] == 'create') {
    $tags = parse_tags($_POST['tags']);
    $sql = "INSERT INTO news (title, body, tags, created_at) VALUES ('" . $_POST['title'] . "', '" . $_POST['body'] . "', '" . implode(',', $tags) . "', NOW())";
    mysql_query($sql);
    $logger->write("Created article: " . $_POST['title']);
}

$result = mysql_query("SELECT id, title, created_at FROM news ORDER BY created_at DESC");
?>
<!DOCTYPE html>
<html>
<head><title>Manage News - School Portal</title></head>
<body>
<h1>Manage News</h1>
<form method="POST" action="manage_news.php">
  <input type="hidden" name="action" value="create">
  <input type="text" name="title" placeholder="Title"><br>
  <textarea name="body" placeholder="Body"></textarea><br>
  <input type="text" name="tags" placeholder="tag1,tag2,tag3"><br>
  <button type="submit">Publish</button>
</form>
<table border="1">
<tr><th>ID</th><th>Title</th><th>Date</th></tr>
<?php while ($row = mysql_fetch_assoc($result)) { ?>
<tr><td><?= $row['id'] ?></td><td><?= $row['title'] ?></td><td><?= $row['created_at'] ?></td></tr>
<?php } ?>
</table>
</body>
</html>
