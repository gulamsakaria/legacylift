<?php
require_once __DIR__ . '/includes/config.php';
$_SESSION = array();
session_destroy();
header("Location: login.php");
exit;
