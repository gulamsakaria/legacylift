<?php
require_once __DIR__ . '/includes/bootstrap.php';
require_once __DIR__ . '/includes/functions.php';

$message = '';

if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $username = clean_input($_POST['username']);
    $email = clean_input($_POST['email']);
    $hashed = md5($_POST['password']);

    $sql = "INSERT INTO users (username, email, password) VALUES ('" . $username . "', '" . $email . "', '" . $hashed . "')";
    mysql_query($sql);

    if (mysql_affected_rows() > 0) {
        $message = "Account created for " . $_POST['username'] . ". You may now log in.";
    } else {
        $message = "Registration failed: " . mysql_error();
    }
}
?>
<!DOCTYPE html>
<html>
<head><title>Register - School Portal</title></head>
<body>
  <h1>Create an Account</h1>
  <p><?= $message ?></p>
  <form method="POST" action="register.php">
    <input type="text" name="username" placeholder="Username"><br>
    <input type="email" name="email" placeholder="Email"><br>
    <input type="password" name="password" placeholder="Password"><br>
    <button type="submit">Register</button>
  </form>
</body>
</html>
