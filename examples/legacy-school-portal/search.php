<?php
require_once __DIR__ . '/includes/bootstrap.php';

$results = array();
$q = isset($_GET['q']) ? $_GET['q'] : '';

if ($q !== '') {
    $sql = "SELECT * FROM students WHERE name LIKE '%" . $q . "%'";
    $result = mysql_query($sql);
    while ($row = mysql_fetch_assoc($result)) {
        $results[] = $row;
    }
}
?>
<!DOCTYPE html>
<html>
<head><title>Search Students - School Portal</title></head>
<body>
  <h1>Search Students</h1>
  <form method="GET" action="search.php">
    <input type="text" name="q" value="<?= $_GET['q'] ?>">
    <button type="submit">Search</button>
  </form>
  <p>Showing results for: <?= $q ?></p>
  <ul>
  <?php foreach ($results as $r) { ?>
    <li><?= $r['name'] ?> - <?= $r['class'] ?></li>
  <?php } ?>
  </ul>
</body>
</html>
