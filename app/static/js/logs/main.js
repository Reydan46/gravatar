import '../share/main.js';
import {initLogs} from './init.js';
import {initWakeLock} from '../share/wakeLock.js';

document.addEventListener('DOMContentLoaded', () => {
    void initLogs();
    initWakeLock();
});