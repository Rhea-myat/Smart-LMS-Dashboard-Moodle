<?php
namespace block_smartlmsdashboard;

defined('MOODLE_INTERNAL') || die();

class prediction_reader {

    public const DEFAULT_RISK_THRESHOLD = 0.50;

    public static function default_course_config(string $coursekey = '', string $courselabel = ''): array {
        return [
            'courseKey' => $coursekey,
            'courseLabel' => $courselabel,
            'teachingMode' => 'Medium',
            'earlyEngagementNotifications' => [
                'week1' => true,
                'week2' => true,
                'week3' => true,
            ],
            'riskThreshold' => self::DEFAULT_RISK_THRESHOLD,
            'notificationTypes' => [
                'newHighRisk' => true,
                'noLmsActivity' => true,
            ],
            'notificationFrequency' => 'Weekly summary',
            'isConfigured' => false,
        ];
    }

    private static function table_columns(string $schema, string $table): array {
        global $DB;

        $records = $DB->get_records_sql("
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema
              AND table_name = :table
        ", [
            'schema' => $schema,
            'table' => $table,
        ]);

        return array_map(static function($record): string {
            return strtolower($record->column_name);
        }, array_values($records));
    }

    private static function first_existing_column(array $columns, array $candidates): ?string {
        foreach ($candidates as $candidate) {
            if (!$candidate) {
                continue;
            }
            if (in_array(strtolower($candidate), $columns, true)) {
                return $candidate;
            }
        }

        return null;
    }

    private static function schema_exists(string $schema): bool {
        global $DB;

        try {
            return (bool)$DB->get_record_sql("
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name = :schema
            ", ['schema' => $schema]);
        } catch (\Exception $exception) {
            return false;
        }
    }

    private static function first_existing_schema(array $schemas): ?string {
        foreach ($schemas as $schema) {
            if (self::schema_exists($schema)) {
                return $schema;
            }
        }

        return null;
    }

    private static function table_exists(string $schema, string $table): bool {
        global $DB;

        try {
            return (bool)$DB->get_record_sql("
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = :schema
                  AND table_name = :table
            ", [
                'schema' => $schema,
                'table' => $table,
            ]);
        } catch (\Exception $exception) {
            return false;
        }
    }

    private static function first_existing_table(string $schema, array $tables): ?string {
        foreach ($tables as $table) {
            if (self::table_exists($schema, $table)) {
                return $table;
            }
        }

        return null;
    }

    private static function sql_identifier(string $identifier): string {
        return '`' . str_replace('`', '``', $identifier) . '`';
    }

    private static function course_column_candidates(): array {
        return [
            'course_key',
            'course_id',
            'courseid',
            'moodle_course_id',
            'moodle_courseid',
            'course_idnumber',
            'courseidnumber',
            'unit_key',
            'unit_id',
            'unitid',
            'module_key',
        ];
    }

    private static function role_filter_sql(string $coursealias): string {
        return "
            EXISTS (
                SELECT 1
                  FROM {context} ctx
                  JOIN {role_assignments} ra ON ra.contextid = ctx.id
                  JOIN {role} r ON r.id = ra.roleid
                 WHERE ctx.contextlevel = 50
                   AND ctx.instanceid = {$coursealias}
                   AND ra.userid = :roleuserid
                   AND r.shortname IN ('teacher', 'editingteacher', 'manager')
            )
        ";
    }

    private static function user_has_manager_role(int $userid): bool {
        global $DB;

        try {
            return (bool)$DB->get_record_sql("
                SELECT ra.id
                  FROM {role_assignments} ra
                  JOIN {role} r ON r.id = ra.roleid
                 WHERE ra.userid = :userid
                   AND r.shortname = 'manager'
                 LIMIT 1
            ", ['userid' => $userid]);
        } catch (\Exception $exception) {
            return false;
        }
    }

    public static function user_can_view_all_units(): bool {
        global $USER;

        $systemcontext = \context_system::instance();

        return is_siteadmin($USER) ||
            has_capability('moodle/site:config', $systemcontext) ||
            has_capability('moodle/site:manageblocks', $systemcontext) ||
            self::user_has_manager_role((int)$USER->id);
    }

    public static function get_allowed_course_keys(): ?array {
        global $DB, $USER;

        if (self::user_can_view_all_units()) {
            return null;
        }

        try {
            $records = $DB->get_records_sql("
                SELECT DISTINCT ctx.instanceid AS courseid
                  FROM {context} ctx
                  JOIN {role_assignments} ra ON ra.contextid = ctx.id
                  JOIN {role} r ON r.id = ra.roleid
                 WHERE ctx.contextlevel = 50
                   AND ra.userid = :userid
                   AND r.shortname IN ('teacher', 'editingteacher')
            ", ['userid' => $USER->id]);
        } catch (\Exception $exception) {
            return [];
        }

        $coursekeys = [];
        foreach ($records as $record) {
            $coursekey = self::moodle_course_id_to_course_key((int)$record->courseid);
            if ($coursekey !== null && $coursekey !== '') {
                $coursekeys[$coursekey] = $coursekey;
            }
        }

        return array_values($coursekeys);
    }

    public static function filter_points_by_course_access(array $points, ?array $allowedcoursekeys): array {
        if ($allowedcoursekeys === null) {
            return $points;
        }

        $allowed = array_flip(array_map('strval', $allowedcoursekeys));

        return array_values(array_filter($points, static function(array $point) use ($allowed): bool {
            return isset($allowed[(string)($point['coursekey'] ?? '')]);
        }));
    }

    public static function build_risk_distribution_from_points(array $points): array {
        $safe = 0;
        $atrisk = 0;

        foreach ($points as $point) {
            if ((int)($point['label'] ?? 0) === 1) {
                $atrisk++;
            } else {
                $safe++;
            }
        }

        return [
            'labels' => [0, 1],
            'values' => [$safe, $atrisk],
        ];
    }

    public static function get_user_course_configs(array $points): array {
        global $DB, $USER;

        $configs = [];
        $labels = [];
        $coursekeys = [];

        foreach ($points as $point) {
            $coursekey = (string)($point['coursekey'] ?? '');
            if ($coursekey === '') {
                continue;
            }
            $coursekeys[$coursekey] = $coursekey;
            if (!isset($labels[$coursekey]) && !empty($point['courselabel'])) {
                $labels[$coursekey] = (string)$point['courselabel'];
            }
        }

        foreach ($coursekeys as $coursekey) {
            $configs[$coursekey] = self::default_course_config($coursekey, $labels[$coursekey] ?? '');
        }

        if (empty($coursekeys)) {
            return $configs;
        }

        try {
            $records = $DB->get_records_list('block_smartlms_course_config', 'course_key', array_values($coursekeys));
        } catch (\Exception $exception) {
            return $configs;
        }

        foreach ($records as $record) {
            if ((int)$record->userid !== (int)$USER->id) {
                continue;
            }

            $coursekey = (string)$record->course_key;
            $configs[$coursekey] = [
                'courseKey' => $coursekey,
                'courseLabel' => $record->course_label ?: ($labels[$coursekey] ?? ''),
                'teachingMode' => $record->teaching_mode ?: 'Medium',
                'earlyEngagementNotifications' => [
                    'week1' => !empty($record->notify_week1_no_activity),
                    'week2' => !empty($record->notify_week2_no_activity),
                    'week3' => !empty($record->notify_week3_no_activity),
                ],
                'riskThreshold' => is_numeric($record->risk_threshold) ?
                    max(0, min(1, (float)$record->risk_threshold)) : self::DEFAULT_RISK_THRESHOLD,
                'notificationTypes' => [
                    'newHighRisk' => !empty($record->notify_new_high_risk),
                    'noLmsActivity' => !empty($record->notify_no_lms_activity),
                ],
                'notificationFrequency' => $record->notification_frequency ?: 'Weekly summary',
                'isConfigured' => true,
            ];
        }

        return $configs;
    }

    private static function course_has_predictions(int $courseid): bool {
        $coursekey = self::moodle_course_id_to_course_key($courseid);

        return $coursekey !== null && $coursekey !== '';
    }

    private static function moodle_course_id_to_course_key(int $courseid): ?string {
        global $DB;

        if ($courseid <= 0) {
            return null;
        }

        $analyticschema = self::first_existing_schema(['analytics_db', 'analytic_db']);
        if ($analyticschema && self::table_exists($analyticschema, 'dim_course')) {
            try {
                $columns = self::table_columns($analyticschema, 'dim_course');
                $courseidcolumn = self::first_existing_column($columns, [
                    'course_id',
                    'courseid',
                    'moodle_course_id',
                    'moodle_courseid',
                    'id',
                ]);
                $coursekeycolumn = self::first_existing_column($columns, [
                    'course_key',
                    'unit_key',
                    'id',
                ]);

                if ($courseidcolumn && $coursekeycolumn) {
                    $record = $DB->get_record_sql("
                        SELECT " . self::sql_identifier($coursekeycolumn) . " AS course_key
                          FROM " . self::sql_identifier($analyticschema) . ".dim_course
                         WHERE CAST(" . self::sql_identifier($courseidcolumn) . " AS CHAR) = CAST(:courseid AS CHAR)
                         LIMIT 1
                    ", ['courseid' => $courseid]);

                    if ($record && $record->course_key !== null && $record->course_key !== '') {
                        return (string)$record->course_key;
                    }
                }
            } catch (\Exception $exception) {
                // Fall through to prediction_result lookup.
            }
        }

        try {
            $columns = self::table_columns('ml_db', 'prediction_result');
            $coursecolumn = self::first_existing_column($columns, self::course_column_candidates());
            if (!$coursecolumn) {
                return null;
            }

            $record = $DB->get_record_sql("
                SELECT " . self::sql_identifier($coursecolumn) . " AS course_key
                  FROM ml_db.prediction_result
                 WHERE CAST(" . self::sql_identifier($coursecolumn) . " AS CHAR) = CAST(:courseid AS CHAR)
                 LIMIT 1
            ", ['courseid' => $courseid]);

            if ($record && $record->course_key !== null && $record->course_key !== '') {
                return (string)$record->course_key;
            }
        } catch (\Exception $exception) {
            return null;
        }

        return null;
    }

    public static function get_default_course_key(?int $currentcourseid = null): ?string {
        global $DB, $USER;

        if ($currentcourseid && $currentcourseid > SITEID && self::course_has_predictions($currentcourseid)) {
            return self::moodle_course_id_to_course_key($currentcourseid);
        }

        $params = ['userid' => $USER->id, 'roleuserid' => $USER->id, 'siteid' => SITEID];
        $rolefilter = self::role_filter_sql('ula.courseid');

        try {
            $records = $DB->get_records_sql("
                SELECT ula.courseid, ula.timeaccess
                  FROM {user_lastaccess} ula
                 WHERE ula.userid = :userid
                   AND ula.courseid <> :siteid
                   AND {$rolefilter}
                 ORDER BY ula.timeaccess DESC
            ", $params, 0, 20);

            foreach ($records as $record) {
                $coursekey = self::moodle_course_id_to_course_key((int)$record->courseid);
                if ($coursekey !== null && $coursekey !== '') {
                    return $coursekey;
                }
            }
        } catch (\Exception $exception) {
            // Fall through to logstore lookup.
        }

        $params = ['userid' => $USER->id, 'roleuserid' => $USER->id, 'siteid' => SITEID];
        $rolefilter = self::role_filter_sql('l.courseid');

        try {
            $records = $DB->get_records_sql("
                SELECT l.courseid, COUNT(1) AS access_count, MAX(l.timecreated) AS last_access
                  FROM {logstore_standard_log} l
                 WHERE l.userid = :userid
                   AND l.courseid IS NOT NULL
                   AND l.courseid <> :siteid
                   AND {$rolefilter}
                 GROUP BY l.courseid
                 ORDER BY access_count DESC, last_access DESC
            ", $params, 0, 20);

            foreach ($records as $record) {
                $coursekey = self::moodle_course_id_to_course_key((int)$record->courseid);
                if ($coursekey !== null && $coursekey !== '') {
                    return $coursekey;
                }
            }
        } catch (\Exception $exception) {
            return null;
        }

        return null;
    }

    public static function get_risk_distribution(): array {
        global $DB;

        try {
            $columns = self::table_columns('ml_db', 'prediction_result');
        } catch (\Exception $exception) {
            $columns = [];
        }

        $coursecolumn = self::first_existing_column($columns, self::course_column_candidates());
        $latestwhere = "p.snapshot_date = (
                SELECT MAX(p2.snapshot_date)
                FROM ml_db.prediction_result p2
            )";

        if ($coursecolumn) {
            $courseidentifier = self::sql_identifier($coursecolumn);
            $latestwhere = "p.snapshot_date = (
                SELECT MAX(p2.snapshot_date)
                FROM ml_db.prediction_result p2
                WHERE (
                    p2.{$courseidentifier} = p.{$courseidentifier}
                    OR (p2.{$courseidentifier} IS NULL AND p.{$courseidentifier} IS NULL)
                )
            )";
        }

        $sql = "
            SELECT final_risk_label, COUNT(DISTINCT student_key) AS total
            FROM ml_db.prediction_result p
            WHERE {$latestwhere}
            GROUP BY final_risk_label
        ";

        $records = $DB->get_records_sql($sql);

        $labels = [];
        $values = [];

        foreach ($records as $record) {
            $labels[] = $record->final_risk_label;
            $values[] = (int)$record->total;
        }

        return [
            'labels' => $labels,
            'values' => $values
        ];
    }

    public static function get_risk_bubble_data(): array {
    global $DB;

    $analyticschema = self::first_existing_schema(['analytics_db', 'analytic_db']);

    try {
        $columns = self::table_columns('ml_db', 'prediction_result');
    } catch (\Exception $exception) {
        $columns = [];
    }

    $coursecolumn = self::first_existing_column($columns, self::course_column_candidates());
    $predictionacademicperiodcolumn = self::first_existing_column($columns, [
        'academic_period_key',
        'academicperiodkey',
        'academic_period_id',
        'academicperiodid',
        'period_key',
        'period_id',
        'teaching_period_key',
        'teaching_period_id',
        'study_period_key',
        'study_period_id',
        'term_key',
        'term_id',
        'semester_key',
        'semester_id',
    ]);
    $predictionidexpression = in_array('prediction_id', $columns, true) ?
        'p.' . self::sql_identifier('prediction_id') : 'NULL';
    $coursekeyexpression = $coursecolumn ?
        'p.' . self::sql_identifier($coursecolumn) : 'NULL';
    $academicperiodkeyexpression = $predictionacademicperiodcolumn ?
        'p.' . self::sql_identifier($predictionacademicperiodcolumn) : null;
    $predictionidselect = $predictionidexpression . ' AS prediction_id';
    $coursekeyselect = $coursekeyexpression . ' AS course_key';
    $coursejoin = '';
    $courselabelselect = "CASE WHEN {$coursekeyexpression} IS NULL THEN 'Unit not recorded' ELSE CONCAT('Unit ', {$coursekeyexpression}) END AS course_label";
    $studentjoin = '';
    $studentnameselect = "CONCAT('Student ', p.student_key) AS student_name";
    $studentemailselect = "'' AS student_email";
    $latestwhere = "p.snapshot_date = (
            SELECT MAX(p2.snapshot_date)
            FROM ml_db.prediction_result p2
        )";

    if ($coursecolumn) {
        $courseidentifier = self::sql_identifier($coursecolumn);
        $latestwhere = "p.snapshot_date = (
            SELECT MAX(p2.snapshot_date)
            FROM ml_db.prediction_result p2
            WHERE (
                p2.{$courseidentifier} = p.{$courseidentifier}
                OR (p2.{$courseidentifier} IS NULL AND p.{$courseidentifier} IS NULL)
            )
        )";
    }

    if ($analyticschema && self::table_exists($analyticschema, 'dim_student')) {
        $studentjoin = "
        LEFT JOIN " . self::sql_identifier($analyticschema) . ".dim_student s
            ON p.student_key = s.student_key";
        $studentnameselect = "COALESCE(s.full_name, CONCAT('Student ', p.student_key)) AS student_name";
        $studentemailselect = "COALESCE(s.email, '') AS student_email";
    }

    if ($analyticschema && $coursecolumn) {
        $coursetable = self::first_existing_table($analyticschema, [
            'dim_course',
            'dim_unit',
            'course',
            'courses',
            'unit',
            'units',
            'dim_module',
        ]);

        if ($coursetable) {
            try {
                $coursecolumns = self::table_columns($analyticschema, $coursetable);
            } catch (\Exception $exception) {
                $coursecolumns = [];
            }

            $coursekeycolumn = self::first_existing_column($coursecolumns, [
                $coursecolumn,
                'course_key',
                'course_id',
                'courseid',
                'moodle_course_id',
                'moodle_courseid',
                'course_idnumber',
                'courseidnumber',
                'unit_key',
                'unit_id',
                'unitid',
                'id',
            ]);
            $coursenamecolumn = self::first_existing_column($coursecolumns, [
                'course_name',
                'course_fullname',
                'fullname',
                'full_name',
                'course_shortname',
                'shortname',
                'short_name',
                'unit_fullname',
                'unit_name',
                'unit_shortname',
                'unit_code',
                'course_code',
                'display_name',
                'title',
                'name',
            ]);
            $coursecodecolumn = self::first_existing_column($coursecolumns, [
                'unit_code',
                'course_code',
                'code',
                'shortcode',
                'course_shortname',
                'shortname',
                'unit_shortname',
                'course_idnumber',
                'idnumber',
            ]);
            $academicperiodcolumn = self::first_existing_column($coursecolumns, [
                'academic_period',
                'academic_period_code',
                'academic_period_label',
                'academicperiod',
                'teaching_period',
                'teaching_period_code',
                'teaching_period_label',
                'teachingperiod',
                'study_period',
                'study_period_code',
                'study_period_label',
                'studyperiod',
                'period_code',
                'period_label',
                'term',
                'term_code',
                'term_label',
                'semester',
                'semester_code',
                'semester_label',
                'period',
                'intake',
                'year_term',
                'academicyear',
                'academic_year',
            ]);
            $academicperiodkeycolumn = self::first_existing_column($coursecolumns, [
                'academic_period_key',
                'academicperiodkey',
                'academic_period_id',
                'academicperiodid',
                'period_key',
                'period_id',
                'teaching_period_key',
                'teaching_period_id',
                'study_period_key',
                'study_period_id',
                'term_key',
                'term_id',
                'semester_key',
                'semester_id',
            ]);

            if ($coursekeycolumn) {
                $coursejoin = "
        LEFT JOIN " . self::sql_identifier($analyticschema) . "." . self::sql_identifier($coursetable) . " c
            ON CAST(c." . self::sql_identifier($coursekeycolumn) . " AS CHAR) = CAST({$coursekeyexpression} AS CHAR)";

                if (!$academicperiodcolumn && ($academicperiodkeyexpression || $academicperiodkeycolumn)) {
                    $periodtable = self::first_existing_table($analyticschema, [
                        'dim_academic_period',
                        'dim_academicperiod',
                        'academic_period',
                        'academic_periods',
                        'dim_teaching_period',
                        'teaching_period',
                        'teaching_periods',
                        'dim_study_period',
                        'study_period',
                        'study_periods',
                        'dim_period',
                        'period',
                        'periods',
                        'dim_term',
                        'term',
                        'terms',
                        'dim_semester',
                        'semester',
                        'semesters',
                    ]);

                    if ($periodtable) {
                        try {
                            $periodcolumns = self::table_columns($analyticschema, $periodtable);
                        } catch (\Exception $exception) {
                            $periodcolumns = [];
                        }

                        $periodkeycolumn = self::first_existing_column($periodcolumns, [
                            $predictionacademicperiodcolumn,
                            $academicperiodkeycolumn,
                            'academic_period_key',
                            'academicperiodkey',
                            'academic_period_id',
                            'academicperiodid',
                            'period_key',
                            'period_id',
                            'teaching_period_key',
                            'teaching_period_id',
                            'study_period_key',
                            'study_period_id',
                            'term_key',
                            'term_id',
                            'semester_key',
                            'semester_id',
                            'id',
                        ]);
                        $periodlabelcolumn = self::first_existing_column($periodcolumns, [
                            'academic_period',
                            'academic_period_code',
                            'academic_period_label',
                            'academicperiod',
                            'academic_period_name',
                            'period_name',
                            'period_code',
                            'period_label',
                            'teaching_period',
                            'teaching_period_name',
                            'teaching_period_code',
                            'teaching_period_label',
                            'study_period',
                            'study_period_name',
                            'study_period_code',
                            'study_period_label',
                            'term_name',
                            'term_code',
                            'term_label',
                            'semester_name',
                            'semester_code',
                            'semester_label',
                            'period',
                            'display_name',
                            'name',
                            'title',
                            'code',
                        ]);

                        if ($periodkeycolumn) {
                            $periodkeyexpression = $academicperiodkeyexpression ?:
                                'c.' . self::sql_identifier($academicperiodkeycolumn);
                            $coursejoin .= "
        LEFT JOIN " . self::sql_identifier($analyticschema) . "." . self::sql_identifier($periodtable) . " ap
            ON CAST(ap." . self::sql_identifier($periodkeycolumn) . " AS CHAR) = CAST({$periodkeyexpression} AS CHAR)";

                            $periodyearcolumn = self::first_existing_column($periodcolumns, [
                                'academic_year',
                                'academicyear',
                                'year',
                            ]);
                            $periodsemestercolumn = self::first_existing_column($periodcolumns, [
                                'semester',
                                'term',
                                'teaching_period',
                                'study_period',
                                'period',
                            ]);

                            if ($periodyearcolumn && $periodsemestercolumn) {
                                $academicperiodcolumn = "CASE
                                    WHEN NULLIF(CAST(ap." . self::sql_identifier($periodsemestercolumn) .
                                        " AS CHAR), '') IS NOT NULL
                                     AND NULLIF(CAST(ap." . self::sql_identifier($periodyearcolumn) .
                                        " AS CHAR), '') IS NOT NULL THEN CONCAT('(', CAST(ap." .
                                            self::sql_identifier($periodsemestercolumn) . " AS CHAR), ', ', CAST(ap." .
                                            self::sql_identifier($periodyearcolumn) . " AS CHAR), ')')
                                    ELSE CONCAT_WS(', ', NULLIF(CAST(ap." .
                                        self::sql_identifier($periodsemestercolumn) . " AS CHAR), ''), NULLIF(CAST(ap." .
                                        self::sql_identifier($periodyearcolumn) . " AS CHAR), ''))
                                END";
                            } else if ($periodlabelcolumn) {
                                $academicperiodcolumn = 'ap.' . self::sql_identifier($periodlabelcolumn);
                            }
                        }
                    }
                }

                if ($coursecodecolumn || $coursenamecolumn || $academicperiodcolumn) {
                    $labelparts = [];

                    if ($coursecodecolumn) {
                        $labelparts[] = "NULLIF(CAST(c." . self::sql_identifier($coursecodecolumn) . " AS CHAR), '')";
                    } else {
                        $labelparts[] = "NULLIF(CAST({$coursekeyexpression} AS CHAR), '')";
                    }
                    if ($coursenamecolumn && $coursenamecolumn !== $coursecodecolumn) {
                        $labelparts[] = "NULLIF(CAST(c." . self::sql_identifier($coursenamecolumn) . " AS CHAR), '')";
                    }
                    if ($academicperiodcolumn) {
                        $periodexpression = strpos($academicperiodcolumn, '.') === false ?
                            'c.' . self::sql_identifier($academicperiodcolumn) : $academicperiodcolumn;
                        $labelparts[] = "NULLIF(CAST({$periodexpression} AS CHAR), '')";
                    }

                    $courselabelselect = "COALESCE(NULLIF(CONCAT_WS(' - ', " . implode(', ', $labelparts) .
                        "), ''), CONCAT('Unit ', {$coursekeyexpression})) AS course_label";
                }
            }
        }
    }

    $sql = "
        SELECT MD5(CONCAT(
                   p.student_key, '|',
                   COALESCE({$predictionidexpression}, ''), '|',
                   COALESCE({$coursekeyexpression}, ''), '|',
                   p.snapshot_date
               )) AS row_key,
               p.student_key,
               {$predictionidselect},
               {$coursekeyselect},
               {$courselabelselect},
               p.snapshot_date,
               {$studentnameselect},
               {$studentemailselect},
               p.behaviour_probability,
               p.academic_probability,
               p.final_risk_probability,
               p.final_risk_label
        FROM ml_db.prediction_result p
        {$studentjoin}
        {$coursejoin}
        WHERE {$latestwhere}
    ";

    $records = $DB->get_records_sql($sql);

    $points = [];

    foreach ($records as $record) {
        $points[] = [
            'x' => (float)$record->behaviour_probability,
            'y' => (float)$record->academic_probability,
            'r' => 4 + ((float)$record->final_risk_probability * 8),
            'student' => (string)$record->student_name,
            'studentid' => (string)$record->student_key,
            'predictionid' => $record->prediction_id !== null ? (string)$record->prediction_id : '',
            'coursekey' => $record->course_key !== null ? (string)$record->course_key : '',
            'courselabel' => $record->course_label !== null ? (string)$record->course_label : '',
            'snapshotdate' => (string)$record->snapshot_date,
            'email' => (string)$record->student_email,
            'risk' => (float)$record->final_risk_probability,
            'label' => (int)$record->final_risk_label
        ];
    }

    return $points;
    }

    public static function get_prediction_metadata(): array {
        global $DB;

        $metadata = [
            'snapshotDate' => null,
            'modelVersion' => null,
            'predictionConfidence' => null,
            'modelMetrics' => [
                'accuracy' => null,
                'recall' => null,
                'f1' => null,
                'rocAuc' => null,
            ],
        ];

        $snapshot = $DB->get_record_sql("
            SELECT MAX(snapshot_date) AS snapshot_date
            FROM ml_db.prediction_result
        ");

        if ($snapshot && !empty($snapshot->snapshot_date)) {
            $metadata['snapshotDate'] = (string)$snapshot->snapshot_date;
        }

        try {
            $columns = self::table_columns('ml_db', 'model_registry');
        } catch (\Exception $exception) {
            return $metadata;
        }

        if (!$columns) {
            return $metadata;
        }

        $versioncolumn = self::first_existing_column($columns, [
            'model_version',
            'version',
            'model_name',
            'name',
        ]);
        $confidencecolumn = self::first_existing_column($columns, [
            'accuracy',
            'prediction_confidence',
            'confidence',
            'validation_accuracy',
        ]);
        $accuracycolumn = self::first_existing_column($columns, [
            'accuracy',
            'validation_accuracy',
        ]);
        $recallcolumn = self::first_existing_column($columns, [
            'recall',
            'validation_recall',
        ]);
        $f1column = self::first_existing_column($columns, [
            'f1',
            'f1_score',
            'validation_f1',
        ]);
        $rocauccolumn = self::first_existing_column($columns, [
            'roc_auc',
            'roc-auc',
            'auc',
            'validation_roc_auc',
        ]);
        $ordercolumn = self::first_existing_column($columns, [
            'created_at',
            'updated_at',
            'trained_at',
            'snapshot_date',
            'id',
        ]);

        if (!$versioncolumn && !$confidencecolumn && !$accuracycolumn && !$recallcolumn && !$f1column && !$rocauccolumn) {
            return $metadata;
        }

        $selects = [];
        $selects[] = $versioncolumn ? self::sql_identifier($versioncolumn) . ' AS model_version' : 'NULL AS model_version';
        $selects[] = $confidencecolumn ?
            self::sql_identifier($confidencecolumn) . ' AS prediction_confidence' : 'NULL AS prediction_confidence';
        $selects[] = $accuracycolumn ? self::sql_identifier($accuracycolumn) . ' AS accuracy' : 'NULL AS accuracy';
        $selects[] = $recallcolumn ? self::sql_identifier($recallcolumn) . ' AS recall' : 'NULL AS recall';
        $selects[] = $f1column ? self::sql_identifier($f1column) . ' AS f1' : 'NULL AS f1';
        $selects[] = $rocauccolumn ? self::sql_identifier($rocauccolumn) . ' AS roc_auc' : 'NULL AS roc_auc';

        $sql = 'SELECT ' . implode(', ', $selects) . ' FROM ml_db.model_registry';
        if ($ordercolumn) {
            $sql .= ' ORDER BY ' . self::sql_identifier($ordercolumn) . ' DESC';
        }
        $sql .= ' LIMIT 1';

        try {
            $record = $DB->get_record_sql($sql);
        } catch (\Exception $exception) {
            return $metadata;
        }

        if ($record) {
            if (!empty($record->model_version)) {
                $metadata['modelVersion'] = (string)$record->model_version;
            }
            if ($record->prediction_confidence !== null && $record->prediction_confidence !== '') {
                $metadata['predictionConfidence'] = (string)$record->prediction_confidence;
            }
            if ($record->accuracy !== null && $record->accuracy !== '') {
                $metadata['modelMetrics']['accuracy'] = (string)$record->accuracy;
            }
            if ($record->recall !== null && $record->recall !== '') {
                $metadata['modelMetrics']['recall'] = (string)$record->recall;
            }
            if ($record->f1 !== null && $record->f1 !== '') {
                $metadata['modelMetrics']['f1'] = (string)$record->f1;
            }
            if ($record->roc_auc !== null && $record->roc_auc !== '') {
                $metadata['modelMetrics']['rocAuc'] = (string)$record->roc_auc;
            }
        }

        return $metadata;
    }
}
