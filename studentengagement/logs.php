<?php

require_once(__DIR__ . '/../../config.php');
//require_login(); 

$PAGE->set_context(context_system::instance());
$PAGE->set_url(new moodle_url('/local/studentengagement/logs.php'));
$PAGE->set_title('Student Logs');
$PAGE->set_heading('Student Logs');

//Load CSV
$file = __DIR__ . '/data/ICT001 S1 2025 Logs RELEASED V1.0.csv';

if(!file_exists($file)){
    die("CSV file not found");
}

$rows = array_map('str_getcsv', file($file));
$header = array_shift($rows);
$header = array_map('trim', $header);
$data = [];

foreach($rows as $row){
    if(count($row) != count($header)){
        continue;
    }

    $data[] = array_combine($header, $row);
}

//Export CSV File (If Needed)
if(isset($_GET['export'])){
    header('Content-Type: text/csv');
    header('Content-Disposition: attachment; filename = "student_logs.csv"');
    $output = fopen('php://output', 'w');
    fputcsv($output, $header);

    foreach($data as $row){
        fputcsv($output, $row);
    }

    fclose($output);
    exit;
}

echo $OUTPUT->header();

//Table Format (CSS Style)
echo "
<style>
body{
    font-family: Arial, sans-serif;
}

h3{
    margin-bottom: 15px;
}

.table-wrapper{
    overflow-x: auto;
}

table{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    background: white;
    min-width: 1200px;
}

th, td{
    padding: 10px 12px;
    border: 1px solid #ddd;
    text-align: left;
    vertical-align: top;
    white-space: nowrap;
}

th{
    color: black;
    font: bold;
    position: sticky;
    top: 0;
}
</style>";

//Page Set-Up
$page = optional_param('page', 0, PARAM_INT);
$perpage = 200;
$totalrecords = count($data);
$start = $page * $perpage;
$pagedata = array_slice($data, $start, $perpage);
$baseurl = new moodle_url('/local/studentengagement/logs.php');

//Table Header
echo "<h4>Student Logs Data</h4>";
echo "<p>Showing " . min($start + $perpage, $totalrecords) . " of $totalrecords</p>";

echo "<p><a href='?export=1'>Export Clean CSV</a></p>";

//Labels (Column)
echo "<div class='table-wrapper'>";
echo "<table>";
echo "<tr>
    <th>Time</th>
    <th>User Full Name</th>
    <th>Username</th>
    <th>Affected User</th>
    <th>Event Context</th>
    <th>Component</th>
    <th>Event Name</th>
    <th>Description</th>
    <th>Origin</th>
    <th>IP Address</th>
</tr>";

//Data (Rows)
foreach($pagedata as $row){
    echo "<tr>
        <td>" . ($row['Time'] ?? '-') . "</td>
        <td>" . ($row['User full name'] ?? '-') . "</td>
        <td>" . ($row['Username'] ?? '-') . "</td>
        <td>" . ($row['Affected user'] ?? '-') . "</td>
        <td>" . ($row['Event context'] ?? '-') . "</td>
        <td>" . ($row['Component'] ?? '-') . "</td>
        <td>" . ($row['Event name'] ?? '-') . "</td>
        <td>" . ($row['Description'] ?? '-') . "</td>
        <td>" . ($row['Origin'] ?? '-') . "</td>
        <td>" . ($row['IP Address'] ?? '-') . "</td>
    </tr>";
}

echo "</table>";
echo "</div>";

//Page Buttons
echo "<div style = 'margin-top:20px;'>";

if($page > 0){
    $prevurl = new moodle_url($baseurl, ['page' => $page - 1]);
    echo "<a href='{$prevurl->out()}' style='margin-right:10px;'>&laquo; Previous</a>";
}

if(($start + $perpage) < $totalrecords){
    $nexturl = new moodle_url($baseurl, ['page' => $page + 1]);
    echo "<a href='{$nexturl->out()}'>Next &raquo;</a>";
}

echo "</div>";
echo $OUTPUT->footer();
