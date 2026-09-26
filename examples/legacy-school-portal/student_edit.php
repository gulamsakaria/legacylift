<?php
require_once __DIR__ . '/includes/bootstrap.php';
require_once __DIR__ . '/includes/functions.php';

if (!isset($_SESSION['user_id'])) {
    header("Location: login.php");
    exit;
}

if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    // Legacy pattern: pull every posted field into a local variable at once.
    extract($_POST);
    $sql = "UPDATE students SET name = '" . $name . "', class = '" . $class . "' WHERE id = '" . $id . "'";
    mysql_query($sql);
    header("Location: student_list.php");
    exit;
}

$id = $_GET['id'];
$sql = "SELECT * FROM students WHERE id = '" . $id . "'";
$result = mysql_query($sql);
$student = mysql_fetch_assoc($result);
?>
<!DOCTYPE html>
<html>
<head><title>Edit Student - School Portal</title></head>
<body>
<h1>Edit Student</h1>
<form method="POST" action="student_edit.php">
  <input type="hidden" name="id" value="<?= $student['id'] ?>">
  <input type="text" name="name" value="<?= $student['name'] ?>"><br>
  <input type="text" name="class" value="<?= $student['class'] ?>"><br>
  <button type="submit">Save Changes</button>
</form>
</body>
</html>
