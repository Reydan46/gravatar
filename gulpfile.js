/**
 * Конфигурация Gulp для минификации ассетов.
 * Задачи экспортируются для независимого вызова из Dockerfile.
 */
const gulp = require('gulp');
const csso = require('gulp-csso');
const terser = require('gulp-terser');

/**
 * Задача для минификации CSS файлов.
 * Берёт все .css файлы, минифицирует и кладёт их на то же место.
 * @return {NodeJS.ReadWriteStream} Поток Gulp.
 */
function minCss() {
    console.log('Running CSS minification...');
    return gulp.src('app/static/css/**/*.css')
        .pipe(csso())
        .pipe(gulp.dest('app/static/css'));
}

/**
 * Задача для минификации JS файлов.
 * Берёт все .js файлы, минифицирует и кладёт их на то же место.
 * @return {NodeJS.ReadWriteStream} Поток Gulp.
 */
function minJs() {
    console.log('Running JavaScript minification...');
    return gulp.src('app/static/js/**/*.js')
        .pipe(terser())
        .pipe(gulp.dest('app/static/js'));
}

// Экспортируем задачи, чтобы их можно было вызывать по имени: `npx gulp minCss`
exports.minCss = minCss;
exports.minJs = minJs;

// Общая задача (на случай перехода минификации всего за раз)
exports.build = gulp.parallel(minCss, minJs);
