<?php
/**
 * Plugin Name: Vulnerable Template Loader (LAB)
 * Description: Odtwarza wzorzec CWE-98 z realnych pluginow WP
 *              (CVE-2025-9993, CVE-2025-7634, CVE-2025-8142 i inne).
 *              CELOWO PODATNY - tylko do labu.
 */
// Wzorzec z realnych pluginow: include() na parametrze z $_GET/$_REQUEST
function vtl_load_template() {
    $tpl = isset($_REQUEST['template']) ? $_REQUEST['template'] : 'default';
    // "zabezpieczenie" jak w realnych pluginach - blokuje tylko http://
    if (preg_match('#^https?://#i', $tpl)) {
        return;
    }
    $path = $tpl;
    if (!file_exists($path)) {
        $path = __DIR__ . '/templates/' . $tpl . '.php';
    }
    include($path);   // <-- SINK
}
add_action('init', 'vtl_load_template');
