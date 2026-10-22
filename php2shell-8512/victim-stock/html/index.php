<?php
// Victim homepage. Writes session with the ini-level handler (php_serialize).
session_start();
if (!isset($_SESSION['visits'])) $_SESSION['visits'] = 0;
$_SESSION['visits']++;
echo "PrefsDemo 1.0 | PHP " . PHP_VERSION . " " . php_sapi_name() .
     " | visits=" . $_SESSION['visits'] .
     " | handler=" . ini_get('session.serialize_handler') . "\n";
