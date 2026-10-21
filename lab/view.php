<?php
// Vulnerable sink: include() on a user-controlled path.
// No extension is appended -> the session file path is accepted as-is.
$tpl = $_GET['tpl'] ?? 'home';
include($tpl);
