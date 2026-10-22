<?php
session_start();
if (!isset($_SESSION['visits'])) $_SESSION['visits'] = 0;
$_SESSION['visits']++;
echo "PrefsDemo 1.0 | PHP " . PHP_VERSION . " " . php_sapi_name() .
     " | visits=" . $_SESSION['visits'] . "\n";
