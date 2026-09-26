<?php
// Shared helper functions — several deprecated patterns (LL006, LL007) live
// here since every page includes this file.

function clean_input($str) {
    // magic_quotes_gpc was removed in PHP 5.4 — this guard is now dead code.
    if (function_exists('get_magic_quotes_gpc') && get_magic_quotes_gpc()) {
        $str = stripslashes($str);
    }
    return trim($str);
}

function parse_tags($tagString) {
    // split() was removed in PHP 7 — legacy comma-splitting of a tag list.
    $tags = split(',', $tagString);
    return array_map('trim', $tags);
}

function is_valid_slug($slug) {
    // ereg() was removed in PHP 7 — legacy slug validation.
    return eregi('^[a-z0-9-]+$', $slug);
}

function load_request_vars() {
    // register_globals-style pattern — recreates every request field as a
    // bare local variable, callers then read $title, $body, etc. directly.
    extract($_REQUEST);
    return get_defined_vars();
}

class legacy_logger {
    var $logfile;

    // Old-style constructor (method named after the class) — LL014.
    function legacy_logger($file = 'activity.log') {
        $this->logfile = $file;
    }

    function write($message) {
        @file_put_contents($this->logfile, $message . "\n", FILE_APPEND);
    }
}
