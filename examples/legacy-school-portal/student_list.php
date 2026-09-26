<?php
require_once __DIR__ . '/includes/bootstrap.php';

$class_filter = isset($_GET['class']) ? $_GET['class'] : '';
if ($class_filter !== '') {
    $sql = "SELECT * FROM students WHERE class = '" . $class_filter . "' ORDER BY name";
} else {
    $sql = "SELECT * FROM students ORDER BY name";
}
$result = mysql_query($sql);
?>
<!DOCTYPE html>
<html>
<head><title>Students - School Portal</title></head>
<body>
<h1>Student List</h1>
<table border="1">
<tr><th>ID</th><th>Name</th><th>Class</th><th>Guardian Phone</th><th>Actions</th></tr>
<?php while ($row = mysql_fetch_assoc($result)) { ?>
<tr>
<?php
    echo "<td>" . $row['id'] . "</td>";
    echo "<td>" . $row['name'] . "</td>";
    echo "<td>" . $row['class'] . "</td>";
    echo "<td>" . $row['guardian_phone'] . "</td>";
    echo "<td><a href='student_edit.php?id=" . $row['id'] . "'>Edit</a></td>";
?>
</tr>
<?php } ?>
</table>
<p><a href="student_add.php">Add new student</a></p>
</body>
</html>
