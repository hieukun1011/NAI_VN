///** @odoo-module **/
import {useComponent, Component, onMounted, useExternalListener, useState } from "@odoo/owl";
import { WebClient } from "@web/webclient/webclient";

const originalSetup = WebClient.prototype.setup;

// Extend the setup method of the WebClient
WebClient.prototype.setup = function () {
    // Call the original setup method
    originalSetup.call(this);

    // Add your custom code here
    this.title.setParts({ zopenerp: "Pontusinc ERP" });
};


