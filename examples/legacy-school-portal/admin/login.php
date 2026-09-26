<?php
require_once __DIR__ . '/../includes/bootstrap.php';

$error = '';
if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $sql = "SELECT * FROM admins WHERE username = '" . $_REQUEST['username'] . "'";
    $result = mysql_query($sql);
    $admin = mysql_fetch_assoc($result);

    if ($admin && $admin['password'] == md5($_REQUEST['password'])) {
        $_SESSION['admin_id'] = $admin['id'];
        $_SESSION['admin_name'] = $admin['username'];
        header("Location: dashboard.php");
        exit;
    } else {
        $error = "Invalid admin credentials";
    }
}
?>
<!DOCTYPE html>
<html>
<head><title>Admin Login</title></head>
<body>
<h1>Admin Login</h1>
<p><?php echo $error; ?></p>
<form method="POST" action="login.php">
  <input type="text" name="username" placeholder="Admin username"><br>
  <input type="password" name="password" placeholder="Password"><br>
  <button type="submit">Login</button>
</form>
</body>
</html>
