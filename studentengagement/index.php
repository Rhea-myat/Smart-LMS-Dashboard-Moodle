<?php

require_once(__DIR__ . '/../../config.php');
require_login();

$PAGE->set_context(context_system::instance());
$PAGE->set_url(new moodle_url('/local/studentengagement/index.php'));
$PAGE->set_title('Student Engagement Dashboard');
$PAGE->set_heading('Student Engagement Dashboard');

echo $OUTPUT->header();

//Load CSV
$file = __DIR__ . '/data/mdl_logs.csv';

if (!file_exists($file)) {
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

//Table Format (CSS Style)
echo "
<style>
body {
    font-family: Arial, sans-serif;
}

h3 {
    margin-bottom: 15px;
}

.table-wrapper {
    overflow-x: auto;
}

table {
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
    background: #2c3e50;
    color: white;
    position: sticky;
    top: 0;
}
</style>
";

//Table
echo "<h4>Student Logs Data</h4>";

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

//Get Data
foreach($data as $row){
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

echo $OUTPUT->footer();
