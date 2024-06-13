odoo.define('pontusinc_employee.InsertFaceId', function (require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var web_client = require('web.web_client');
    var session = require('web.session');
    var _t = core._t;
    var QWeb = core.qweb;
    var self = this;
    var currency;
    var face_list = {
        "is_success": true,
        "msg": "",
        "res": {
            "base64_faces": [],
            "face_align": []
        }
    };
    var DashBoard = AbstractAction.extend({
        contentTemplate: 'InsertFaceEmployee',
        events: {
            'click #uploadPreview': function () {
                fileInput.click(); // Trigger file input click event
            },
            'change #fileInput': function () {
                if (fileInput.files.length > 0) {
                    var reader = new FileReader(); // Create FileReader object
                    reader.onload = function (e) {
                        imagePreview.src = e.target.result; // Set image preview source to the selected file
                    }
                    reader.readAsDataURL(fileInput.files[0]); // Read the selected file as data URL
                }
            },

            'submit #imageForm': function (event) {
                event.preventDefault(); // Prevent the default form submission
                var selectedImage = null;
                // Get the selected file from the file input
                var fileInput = document.getElementById('fileInput');
                var file = fileInput.files[0];
                var self = this;
                rpc.query({
                    model: 'hr.employee',
                    method: 'action_post_facedetection_icommface',
                    args: [this.searchModelConfig.context.active_id, imagePreview.src]
                })
                .then(function (result) {
                    result.res.base64_faces.forEach(function(base64, index) {
                        var imageContainer = document.getElementById("imageContainer"); // Get image container element
                        var col = document.createElement("div"); // Create new column
                        col.className = "col-md-4 mb-4"; // Set column class
                        var imageItem = document.createElement("div"); // Create new image item
                        imageItem.className = "image-item"; // Set image item class
                        var image = $("<img>").attr("src", base64);
//                        var image = document.createElement("img"); // Create new image element
//                        image.src = base64; // Set image source to the uploaded file
                        image.className = "img-fluid"; // Set image class
                        var span = document.createElement("span"); // Create new span element
                        image.on("click", function() {
                            if (this.className == 'selected-image') {
                                selectedImage.removeClass("selected-image");
                                face_list.res.base64_faces = self.removeValueFromArray(base64, face_list.res.base64_faces);
                                face_list.res.face_align = self.removeValueFromArray(result.res.face_align[index], face_list.res.face_align);
                            }else{
                                $(this).addClass("selected-image");
                                face_list.res.base64_faces.push(base64);
                                face_list.res.face_align.push(result.res.face_align[index]);
                            };
                            selectedImage = $(this); // Update selected image
                        });
                        imageItem.append(image[0]); // Append image to image item
                        imageItem.append(span); // Append span to image item
                        col.append(imageItem); // Append image item to column
                        imageContainer.append(col); // Append column to image container
                    });
                })
            },

            'click #rpcButton': function () {
                rpc.query({
                    model: 'hr.employee',
                    method: 'action_insert_user_face_hrm',
                    args: [this.searchModelConfig.context.active_id, face_list]
                })
                return this.do_action({ type: "ir.actions.act_window_close" });
            },
        },


        init: function(parent, context) {
            this._super(parent, context);

            this.dashboards_templates = ['InsertBody'];
        },

        willStart: function(){
            var self = this;
            return this._super()
            .then(function() {
                return $.when();
            });
        },

        start: function() {
            var self = this;

            this.set("title", 'Dashboard');
            return this._super().then(function() {
                self.render_dashboards();
                self.$el.parent().addClass('oe_background_grey');
            });
        },

        removeValueFromArray: function(value, array) {
            return array.filter(function(item) {
                return item !== value;
            });
        },

        render_dashboards: function() {
            var self = this;
            var templates = ['InsertBody']
            _.each(templates, function(template) {
                self.$('.o_hr_dashboard').append(QWeb.render(template, {widget: self}));
            });
        },

    });

    core.action_registry.add('insert_face_cam_checkin', DashBoard);
    return DashBoard;
});