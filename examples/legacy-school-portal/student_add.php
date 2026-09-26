<?php
require_once __DIR__ . '/includes/bootstrap.php';

if (!isset($_SESSION['user_id'])) {
    header("Location: login.php");
    exit;
}

$message = '';
if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $sql = "INSERT INTO students (name, class, guardian_phone) VALUES ('" . $_POST['name'] . "', '" . $_POST['class'] . "', '" . $_POST['guardian_phone'] . "')";
    mysql_query($sql);
    $message = "Student " . $_POST['name'] . " added with ID " . mysql_insert_id();
}
?>
<!DOCTYPE html>
<html>
<head><title>Add Student - School Portal</title></head>
<body>
<h1>Add New Student</h1>
<p><?php echo $message; ?></p>
<form method="POST" action="student_add.php">
  <input type="text" name="name" placeholder="Full name"><br>
  <input type="text" name="class" placeholder="Class"><br>
  <input type="text" name="guardian_phone" placeholder="Guardian phone"><br>
  <button type="submit">Add Student</button>
</form>
</body>
</html>
