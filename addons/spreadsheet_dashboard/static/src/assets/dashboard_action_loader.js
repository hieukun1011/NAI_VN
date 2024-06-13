<<<<<<< HEAD
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { loadSpreadsheetAction } from "@spreadsheet/assets_backend/spreadsheet_action_loader";

const actionRegistry = registry.category("actions");

const loadDashboardAction = async (env, context) => {
    await loadSpreadsheetAction(env, "action_spreadsheet_dashboard", loadDashboardAction);
    return {
        ...context,
        target: "current",
        tag: "action_spreadsheet_dashboard",
        type: "ir.actions.client",
    };
};

actionRegistry.add("action_spreadsheet_dashboard", loadDashboardAction);
=======
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { loadSpreadsheetAction } from "@spreadsheet/assets_backend/spreadsheet_action_loader";

const actionRegistry = registry.category("actions");

const loadDashboardAction = async (env, context) => {
    await loadSpreadsheetAction(env, "action_spreadsheet_dashboard", loadDashboardAction);
    return {
        ...context,
        target: "current",
        tag: "action_spreadsheet_dashboard",
        type: "ir.actions.client",
    };
};

actionRegistry.add("action_spreadsheet_dashboard", loadDashboardAction);
>>>>>>> 1edc56903ab79c74a4459e1792ad6ae33a23a2ad
