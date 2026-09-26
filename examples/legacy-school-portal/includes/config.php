<?php
// Site-wide configuration. Hard-coded credentials (LL011) and legacy
// mysql_* connection (LL001) — typical of a PHP 5.x-era small site.
$db_host = "localhost";
$db_user = "root";
$db_password = "sch00lP0rtal!2011";
$db_name = "legacy_school_portal";

error_reporting(0);
ini_set('display_errors', 1);

session_start();
