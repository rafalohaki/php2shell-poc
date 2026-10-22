<?php
// Gadget wariant "exec": destruktor wywoluje komende wprost (bez zapisu pliku).
class CmdExec {
    public $cmd;
    public function __destruct() { if ($this->cmd) { @system($this->cmd); } }
}
