<?php
/**
 * Realistyczny sink: include() bez walidacji wrapperow.
 * Wiele realnych aplikacji tak robi (template engine, page loader).
 */
$tpl = $_GET['tpl'] ?? 'home';
include($tpl);
