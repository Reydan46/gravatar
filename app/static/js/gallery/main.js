import '../share/main.js';
import {initGallery} from './init.js';
import {initWakeLock} from '../share/wakeLock.js';

document.addEventListener('DOMContentLoaded', () => {
    void initGallery();
    initWakeLock();
});