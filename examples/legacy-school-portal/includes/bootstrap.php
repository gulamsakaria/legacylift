<?php
require_once __DIR__ . '/config.php';

// Old-style database connection (LL001) using credentials from config.php.
$conn = mysql_connect($db_host, $db_user, $db_password);
if (!$conn) {
    die("Could not connect: " . mysql_error());
}
mysql_select_db($db_name, $conn);
