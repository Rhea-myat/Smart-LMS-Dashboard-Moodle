<?php

require_once(__DIR__ . '/../../config.php');
//require_login();

$PAGE->set_context(context_system::instance());
$PAGE->set_url(new moodle_url('/local/studentengagement/results.php'));
$PAGE->set_title('Student Results');
$PAGE->set_heading('Student Results');

//Load CSV
$file = __DIR__ . '/data/ICT001_s1_2025_RESULTS_ALL_MARKS_RELEASED_v1.0(6076970).csv';

if(!file_exists($file)){
    die("CSV file not found");
}

$rows = array_map('str_getcsv', file($file));
array_shift($rows); 
array_shift($rows); 
$header = array_map('trim', array_shift($rows));

$data = [];

foreach($rows as $row){
    if(!is_array($row)){
        continue;
    }

    if(count(array_filter($row)) == 0){
        continue;
    }

    foreach($row as $i => $value){
        if(is_string($value) && strpos($value, '#REF') !== false){
            $row[$i] = '';
        }
    }

    $data[] = array_combine($header, array_pad($row, count($header), ''));
}

//Export CSV File (If Needed)
if(isset($_GET['export'])){
    header('Content-Type: text/csv');
    header('Content-Disposition: attachment; filename = "student_results.csv"');
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
    color: black;
    font: bold;
    position: sticky;
    top: 0;
}
</style>";

$totalrecords = count($data);

//Table Header
echo "<h4>Student Results Data</h4>";
echo "<p>Showing $totalrecords of $totalrecords</p>";

echo "<p><a href='?export=1'>Export Clean CSV</a></p>";

//Labels (Column)
echo "<div class='table-wrapper'>";
echo "<table>";
echo "<tr>
    <th>Person ID</th>
    <th>Surname</th>
    <th>Mark</th>
    <th>Grade</th>
    <th>Ass Ex 1</th>
    <th>Ass Ex 2</th>
    <th>Ass Ex 3</th>
    <th>Ass Ex 4</th>
    <th>Ass Ex 5</th>
    <th>Ass Ex 6</th>
    <th>Ass Ex 7</th>
    <th>Ass Ex 8</th>
    <th>Ass Ex 9</th>
    <th>Ass Ex 10</th>
    <th>Weekly Lab Quizzes /100</th>
    <th>Assignment 1 /100</th>
    <th>Delay (days)</th>
    <th>Ass 1 with Penalty /100</th>
    <th>Ass 2 /100</th>
    <th>Delay (days)</th>
    <th>Ass 2 with Penalty /100</th>
    <th>Exam /100</th>
    <th>Total /100</th>
    <th>Rounded Total /100</th>
    <th>Cal G</th>
</tr>"; 

//Data (Rows)
foreach($data as $row){
    echo "<tr>
        <td>" . ($row['Person Id'] ?? '-') . "</td>
        <td>" . ($row['Surname'] ?? '-') . "</td>
        <td>" . ($row['Mark'] ?? '-') . "</td>
        <td>" . ($row['Grade'] ?? '-') . "</td>
        <td>" . ($row['Ass Ex 1'] ?? '-') . "</td>
        <td>" . ($row['Ass Ex 2'] ?? '-') . "</td>
        <td>" . ($row['Ass Ex 3'] ?? '-') . "</td>
        <td>" . ($row['Ass Ex 4'] ?? '-') . "</td>
        <td>" . ($row['Ass Ex 5'] ?? '-') . "</td>
        <td>" . ($row['Ass Ex 6'] ?? '-') . "</td>
        <td>" . ($row['Ass Ex 7'] ?? '-') . "</td>
        <td>" . ($row['Ass Ex 8'] ?? '-') . "</td>
        <td>" . ($row['Ass Ex 9'] ?? '-') . "</td>
        <td>" . ($row['Ass Ex 10'] ?? '-') . "</td>
        <td>" . ($row['Weekly Lab Quizzes / 100'] ?? '-') . "</td>
        <td>" . ($row['Assignment 1 / 100'] ?? '-') . "</td>
        <td>" . ($row['Delay (days)'] ?? '-') . "</td>
        <td>" . ($row['Ass 1 with Penalty /100'] ?? '-') . "</td>
        <td>" . ($row['Ass 2 /100'] ?? '-') . "</td>
        <td>" . ($row['Delay (days)'] ?? '-') . "</td>
        <td>" . ($row['Ass 2 with Penalty /100'] ?? '-') . "</td>
        <td>" . ($row['Exam/ 100'] ?? '-') . "</td>
        <td>" . ($row['Total/ 100'] ?? '-') . "</td>
        <td>" . ($row['Rounded Total/ 100'] ?? '-') . "</td>
        <td>" . ($row['Cal G'] ?? '-') . "</td>
    </tr>";
}

echo "</table>";
echo "</div>";
echo $OUTPUT->footer();