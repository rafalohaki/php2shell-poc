<?php
// Realistic gadget surface: a deferred cache writer (destructor side effect)
// and a stats logger — patterns common in real apps.
class DeferredWriter {
    public $path; public $data;
    public function __destruct() { @file_put_contents($this->path, $this->data); }
}
