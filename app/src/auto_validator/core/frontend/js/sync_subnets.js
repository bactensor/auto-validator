import * as Diff2Html from 'diff2html';
import 'diff2html/bundles/css/diff2html.min.css';

document.addEventListener('DOMContentLoaded', () => {
    const diff_str = document.getElementById('diff_str').textContent;
    const githubData = document.getElementById('github_data').textContent;
    if (diff_str === '') {
        document.getElementById('diff').innerHTML = '<h2>No changes found</h2>';
        return;
    }
    const decodedDiffStr = decodeURIComponent(JSON.parse('"' + diff_str.replace(/\"/g, '\\"') + '"'));
    const diffHtml = Diff2Html.html(
        decodedDiffStr,
        { drawFileList: false, matching: 'lines', outputFormat: 'side-by-side' }
    );
    document.getElementById('diff').innerHTML = diffHtml;
    document.getElementById('new_data').value = JSON.stringify(githubData);
});