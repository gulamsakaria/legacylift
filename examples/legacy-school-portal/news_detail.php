<?php
require_once __DIR__ . '/includes/bootstrap.php';

$id = $_GET['id'];
$sql = "SELECT * FROM news WHERE id = '" . $id . "'";
$result = mysql_query($sql);
$article = mysql_fetch_assoc($result);
?>
<!DOCTYPE html>
<html>
<head><title><?= $article['title'] ?> - School Portal</title></head>
<body>
  <h1><?= $article['title'] ?></h1>
  <p>Requested article ID: <?= $_GET['id'] ?></p>
  <div><?php echo $article['body']; ?></div>
  <a href="index.php">Back to news</a>
</body>
</html>
