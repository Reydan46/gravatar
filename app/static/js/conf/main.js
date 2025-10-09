import '../share/main.js';
import {initConf} from './init.js';
import {initTooltip} from '../share/tooltip.js';

document.addEventListener('DOMContentLoaded', async () => {
    initTooltip();
    await initConf();
});