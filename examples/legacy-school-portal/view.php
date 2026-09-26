<?php
require_once __DIR__ . '/includes/bootstrap.php';

// "Print-friendly" template picker — lets a page choose which partial to
// render. Never validated against an allow-list, so a request can walk the
// filesystem or pull in a remote file (LFI/RFI).
include(__DIR__ . '/templates/' . $_GET['tpl'] . '.phtml');
