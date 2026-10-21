<?php
// PixelVault-style: upload endpoint
$msg = "upload ok";
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_FILES['image'])) $msg = "saved: " . basename($_FILES['image']['name']);
}
?>
<h1>PixelVault</h1><p><?= htmlspecialchars($msg) ?></p>
