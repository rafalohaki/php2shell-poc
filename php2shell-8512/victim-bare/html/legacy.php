<?php
// Legacy endpoint: old compatibility shim forces the LEGACY php handler
// before reading the session (read/write mismatch = Zero1 gap A).
require __DIR__ . "/lib.php";
header("Content-Type: text/plain");
ini_set('session.serialize_handler', 'php');   // <-- legacy shim
session_start();
echo "[legacy] handler=" . ini_get('session.serialize_handler') .
     " vars=" . count($_SESSION) . "\n";
