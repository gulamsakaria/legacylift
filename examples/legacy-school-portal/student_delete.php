<?php
require_once __DIR__ . '/includes/bootstrap.php';

if (!isset($_SESSION['user_id'])) {
    header("Location: login.php");
    exit;
}

if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $sql = "DELETE FROM students WHERE id = '" . $_POST['id'] . "'";
    mysql_query($sql);
    header("Location: student_list.php?deleted=" . $_POST['id']);
    exit;
}
?>
<!DOCTYPE html>
<html>
<head><title>Delete Student</title></head>
<body>
<h1>Confirm Delete</h1>
<form method="POST" action="student_delete.php">
  <input type="hidden" name="id" value="<?= $_GET['id'] ?>">
  <button type="submit">Confirm Delete</button>
</form>
</body>
</html>
