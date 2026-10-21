<?php
/**
 * Odtworzenie wzorca Laravel View::file() / Blade template path traversal.
 *
 * Realne odpowiedniki (CWE-98 / CWE-22 w ekosystemie Laravel):
 *   - View::file($userPath)           -> compile/include na sciezce usera
 *   - Blade::compileString(file_get)  -> j.w.
 *   - debug-mode Ignition          (CVE-2021-3129 - ale to RCE przez log)
 *
 * Ten lab pokazuje SAM WZORZEC: include() na sciezce z requestu,
 * tak jak robi to View::file() w kodzie aplikacji.
 */
function view_file($path) {
    // Laravel: View::file() wymaga istniejacego pliku i konczy sie .php/.blade.php
    if (!file_exists($path)) {
        http_response_code(404);
        echo "View not found: " . htmlspecialchars($path);
        return;
    }
    // Blade kompiluje do PHP i includuje - tu uproszczone do include()
    include($path);
}

// typowy kontroler: ?view=... lub ?template=...
$tpl = $_REQUEST['view'] ?? $_REQUEST['template'] ?? null;
if ($tpl !== null) {
    view_file($tpl);
} else {
    echo "OK (podaj ?view=)\n";
}
