<?php
// This file is part of Moodle - http://moodle.org/

defined('MOODLE_INTERNAL') || die();

/**
 * Upgrade steps for block_smartlmsdashboard.
 *
 * @param int $oldversion
 * @return bool
 */
function xmldb_block_smartlmsdashboard_upgrade($oldversion) {
    global $DB;

    $dbman = $DB->get_manager();

    if ($oldversion < 2026070700) {
        $table = new xmldb_table('block_smartlms_course_config');

        $table->add_field('id', XMLDB_TYPE_INTEGER, '10', null, XMLDB_NOTNULL, XMLDB_SEQUENCE, null);
        $table->add_field('course_key', XMLDB_TYPE_CHAR, '100', null, XMLDB_NOTNULL, null, null);
        $table->add_field('course_label', XMLDB_TYPE_CHAR, '255', null, null, null, null);
        $table->add_field('userid', XMLDB_TYPE_INTEGER, '10', null, XMLDB_NOTNULL, null, null);
        $table->add_field('teaching_mode', XMLDB_TYPE_CHAR, '20', null, XMLDB_NOTNULL, null, 'Medium');
        $table->add_field('notify_week1_no_activity', XMLDB_TYPE_INTEGER, '1', null, XMLDB_NOTNULL, null, '1');
        $table->add_field('notify_week2_no_activity', XMLDB_TYPE_INTEGER, '1', null, XMLDB_NOTNULL, null, '1');
        $table->add_field('notify_week3_no_activity', XMLDB_TYPE_INTEGER, '1', null, XMLDB_NOTNULL, null, '1');
        $table->add_field('risk_threshold', XMLDB_TYPE_NUMBER, '5, 2', null, XMLDB_NOTNULL, null, '0.50');
        $table->add_field('notify_new_high_risk', XMLDB_TYPE_INTEGER, '1', null, XMLDB_NOTNULL, null, '1');
        $table->add_field('notify_no_lms_activity', XMLDB_TYPE_INTEGER, '1', null, XMLDB_NOTNULL, null, '1');
        $table->add_field('notify_assessment_reminder', XMLDB_TYPE_INTEGER, '1', null, XMLDB_NOTNULL, null, '0');
        $table->add_field('assessment_reminder_days', XMLDB_TYPE_INTEGER, '2', null, XMLDB_NOTNULL, null, '3');
        $table->add_field('notification_frequency', XMLDB_TYPE_CHAR, '40', null, XMLDB_NOTNULL, null, 'Weekly summary');
        $table->add_field('timecreated', XMLDB_TYPE_INTEGER, '10', null, XMLDB_NOTNULL, null, '0');
        $table->add_field('timemodified', XMLDB_TYPE_INTEGER, '10', null, XMLDB_NOTNULL, null, '0');

        $table->add_key('primary', XMLDB_KEY_PRIMARY, ['id']);
        $table->add_index('course_user_uix', XMLDB_INDEX_UNIQUE, ['course_key', 'userid']);
        $table->add_index('userid_ix', XMLDB_INDEX_NOTUNIQUE, ['userid']);

        if (!$dbman->table_exists($table)) {
            $dbman->create_table($table);
        }

        upgrade_block_savepoint(true, 2026070700, 'smartlmsdashboard');
    }

    if ($oldversion < 2026070701) {
        $table = new xmldb_table('block_smartlms_course_config');
        $field = new xmldb_field('assessment_reminder_days', XMLDB_TYPE_INTEGER, '2', null, XMLDB_NOTNULL, null, '3', 'notify_assessment_reminder');

        if ($dbman->table_exists($table) && !$dbman->field_exists($table, $field)) {
            $dbman->add_field($table, $field);
        }

        upgrade_block_savepoint(true, 2026070701, 'smartlmsdashboard');
    }

    if ($oldversion < 2026070702) {
        $table = new xmldb_table('block_smartlms_course_config');

        if ($dbman->table_exists($table)) {
            $assessmentdaysfield = new xmldb_field('assessment_reminder_days');
            if ($dbman->field_exists($table, $assessmentdaysfield)) {
                $dbman->drop_field($table, $assessmentdaysfield);
            }

            $assessmentfield = new xmldb_field('notify_assessment_reminder');
            if ($dbman->field_exists($table, $assessmentfield)) {
                $dbman->drop_field($table, $assessmentfield);
            }
        }

        upgrade_block_savepoint(true, 2026070702, 'smartlmsdashboard');
    }

    return true;
}
