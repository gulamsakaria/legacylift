<? // short open tag, no full <?php
require_once __DIR__ . '/includes/bootstrap.php';

$sent = false;
if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $name = $_POST['name'];
    $msg = $_POST['message'];
    $sql = "INSERT INTO contact_messages (name, message, submitted_at) VALUES ('" . $name . "', '" . $msg . "', NOW())";
    mysql_query($sql);
    $sent = true;
}
?>
<!DOCTYPE html>
<html>
<head><title>Contact Us - School Portal</title></head>
<body>
<h1>Contact Us</h1>
<?php if ($sent) { ?>
  <p>Thanks, <?= $_POST['name'] ?>! Your message has been received.</p>
<?php } ?>
<form method="POST" action="contact.php">
  <input type="text" name="name" placeholder="Your name"><br>
  <textarea name="message" placeholder="Your message"></textarea><br>
  <button type="submit">Send</button>
</form>
</body>
</html>
