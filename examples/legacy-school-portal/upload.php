<?php
require_once __DIR__ . '/includes/bootstrap.php';

if (!isset($_SESSION['user_id'])) {
    header("Location: login.php");
    exit;
}

$status = '';
if ($_SERVER['REQUEST_METHOD'] == 'POST' && isset($_FILES['document'])) {
    $dest = __DIR__ . '/uploads/' . $_FILES['document']['name'];
    if (move_uploaded_file($_FILES['document']['tmp_name'], $dest)) {
        $sql = "INSERT INTO documents (filename, uploaded_by) VALUES ('" . $_FILES['document']['name'] . "', '" . $_SESSION['user_id'] . "')";
        mysql_query($sql);
        $status = "File uploaded successfully.";
    } else {
        $status = "Upload failed.";
    }
}
?>
<!DOCTYPE html>
<html>
<head><title>Upload Document - School Portal</title></head>
<body>
<h1>Upload Document</h1>
<p><?php echo $status; ?></p>
<form method="POST" action="upload.php" enctype="multipart/form-data">
  <input type="file" name="document">
  <button type="submit">Upload</button>
</form>
</body>
</html>
