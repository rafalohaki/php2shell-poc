<?php
/**
 * Samodzielny test wzorca CWE-98 z pluginow WP.
 * Odtwarza dokladnie ta sama logike co plugin.php, bez WordPress core
 * (unia zaleznosci: add_action/init).
 */
function add_action($a, $b) { /* noop - lab */ }
function vtl_load_template() {
    $tpl = isset($_REQUEST['template']) ? $_REQUEST['template'] : 'default';
    if (preg_match('#^https?://#i', $tpl)) { return; }
    $path = $tpl;
    if (!file_exists($path)) {
        $path = __DIR__ . '/templates/' . $tpl . '.php';
    }
    include($path);
}
vtl_load_template();
