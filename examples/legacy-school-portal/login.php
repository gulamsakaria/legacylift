<?php
require_once __DIR__ . '/includes/bootstrap.php';

$error = '';

if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $sql = "SELECT * FROM users WHERE username = '" . $_POST['username'] . "'";
    $result = mysql_query($sql);
    $row = mysql_fetch_assoc($result);

    if ($row && $row['password'] == md5($_POST['password'])) {
        $_SESSION['user_id'] = $row['id'];
        $_SESSION['username'] = $row['username'];
        header("Location: index.php?welcome=" . $_GET['ref']);
        exit;
    } else {
        $error = "Invalid username or password";
    }
}
?>
<!DOCTYPE html>
<html>
<head><title>Login - School Portal</title></head>
<body>
  <h1>Student / Staff Login</h1>
  <?php if ($error) { echo $error; } ?>
  <form method="POST" action="login.php">
    <label>Username: <input type="text" name="username"></label><br>
    <label>Password: <input type="password" name="password"></label><br>
    <button type="submit">Login</button>
  </form>
  <p><a href="register.php">Create an account</a></p>
</body>
</html>
