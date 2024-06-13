odoo.define('hrm_maintenance.countdown_time.js', function (require) {
"use strict";
var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');
var time = require('web.time');
var FieldManagerMixin = require('web.FieldManagerMixin');
var rpc = require('web.rpc')

var _t = core._t;

console.log(AbstractField, '+++++++++++++++++++++++++++++')
var TimeCounter  = AbstractField.extend({
        willStart: function () {
        var self = this;
//        print(self, "+++++++++++++++")
        var def = this._rpc({
            model: 'hr.maintenance.request',
            method: 'search_read',
            domain:  [['id', '=', this.res_id]],
        }).then(function (result) {
        console.log(self, '+++++++++++++')
        console.log(self.mode, 'bbbbbbbbbbbbbbbbbbbbb')
            if (self.mode === 'readonly') {
                var currentDate = new Date();
                self.duration = 0;
                console.log(result,'////////////////////////////')
                console.log(currentDate,'<<<<<<<<<<<<<<<<<<<<<<<<>>>>>>>>>>>>>>>>>>>>>>>>')
                _.each(result, function (data) {
                    console.log(data, '...........................')

                    if (data.state == 'doing'){
                        console.log('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
                        self.duration += data.deadline - currentDate ?
//                        console.log(self.duration, ',,,,,,,,,,,,,,,,,,,,,,,,,,,,,,')
                        self._getDateDifference(data.request_date, data.deadline):
                        self._getDateDifference(currentDate, time.auto_str_to_date(data.deadline));
                    }
                    else{
                        console.log(time.auto_str_to_date(data.deadline) - time.auto_str_to_date(data.close_date),'||||||||||||||||||||||||||')
                        self.duration += time.auto_str_to_date(data.deadline) - time.auto_str_to_date(data.close_date) ?
                        self._getDateDifference(data.close_date, data.deadline):
                        self._getDateDifference(currentDate, time.auto_str_to_date(data.deadline));
                    }
//                    self.duration += data.deadline - currentDate ?
////                        console.log(self.duration, ',,,,,,,,,,,,,,,,,,,,,,,,,,,,,,')
//                        self._getDateDifference(data.request_date, data.deadline):
//                        self._getDateDifference(currentDate, time.auto_str_to_date(data.deadline));
                });
            }
        });
        console.log(def, '_______________________')
        return $.when(this._super.apply(this, arguments), def);
    },

    destroy: function () {
        this._super.apply(this, arguments);
        clearTimeout(this.timer);
    },
    isSet: function () {
        return true;
    },
    _getDateDifference: function (dateStart, dateEnd) {
        console.log(dateStart, '""""""""""""""""""""""""')
        console.log(self, ',,,,,,,,,,,,,,,,,,,,,,,,,,,,')
        console.log(dateEnd,'{[[[[[[[[[[[[[[[[[[[[[[')
        console.log(moment(dateEnd).diff(moment(dateStart)), '$$$$$$$$$$$$$$$$$$$$$$$$$$')
        return moment(dateEnd).diff(moment(dateStart));
    },

    _render: function () {
    console.log(this._startTimeCounter(), '>>>>>>>>>>>>>>>>>>>>>>>>>>>')
        this._startTimeCounter();
    },

    _startTimeCounter: function () {
        var self = this;
        clearTimeout(this.timer);
        console.log(this,'<?<?<?<?<?<?<?<?<?<?<?<?<<?<?<?<?<?<?<')
        console.log(this.duration)
        if (self['recordData']['state'] == 'done' || self['recordData']['state'] == 'cancel' || self['recordData']['state'] == 'closed' ){
            console.log('&*&*&*&*&*&*&*&*&#$%^&*($%^&*()')
            clearTimeout(this.timer);
            console.log((this.duration/1000)/(self['recordData']['the_average_time'] *60),'EYTB^%&^(*)(&%^&GHB&^R&Y(INFH()U(')

        }
        else if (this.duration > 0 && self['recordData']['state'] == 'doing') {
            console.log('VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVYGUG*U*GUY*GUYGYG')
            this.timer = setTimeout(function () {

                self.duration -= 1000;
                console.log(self.duration)
                self._startTimeCounter();
            }, 1000);

        } else {
            clearTimeout(this.timer);
            console.log((this.duration/1000)/(self['recordData']['the_average_time'] *60), '()()()(^&^%&TBJKOIJY&GYGBYG^TGUNJHYG')
            rpc.query({
                model: 'hr.maintenance.request',
                method: 'rpc_render_completed_process',
                args: [[self.res_id], Math.floor((((this.duration/1000)/(self['recordData']['the_average_time'] *60)) *100))],
                });
        }
        console.log(this.duration, 'this.durationthis.durationthis.durationthis.durationthis.durationthis.durationthis.duration')
        if (Math.floor((((this.duration/1000)/(self['recordData']['the_average_time'] *60)) *100)) <= 100 && Math.floor((((this.duration/1000)/(self['recordData']['the_average_time'] *60)) *100)) >= 66){
            this.$el.html($('<div class="progress-bar  bg-success" id="progress" name="progressbar" role="progressbar" style="width:'+ Math.floor((((this.duration/1000)/(self['recordData']['the_average_time'] *60)) *100))+"%" + ';' + 'transition: .2s" aria-valuenow="25" aria-valuemin="0" aria-valuemax="100">' + Math.floor((((this.duration/1000)/(self['recordData']['the_average_time'] *60)) *100)) + '%' + '</div>'));
//            document.getElementById("progress").style.width = Math.floor((((this.duration/1000)/(self['recordData']['the_average_time'] *60)) *100))+"%"
        }
        else if (Math.floor((((this.duration/1000)/(self['recordData']['the_average_time'] *60)) *100)) >= 33){
            this.$el.html($('<div class="progress-bar  bg-warning" id="progress" name="progressbar" role="progressbar" style="width:'+ Math.floor((((this.duration/1000)/(self['recordData']['the_average_time'] *60)) *100))+"%" + ';' + 'transition: .2s" aria-valuenow="25" aria-valuemin="0" aria-valuemax="100">' + Math.floor((((this.duration/1000)/(self['recordData']['the_average_time'] *60)) *100)) + '%' + '</div>'));
        }
        else if (Math.floor((((this.duration/1000)/(self['recordData']['the_average_time'] *60)) *100)) < 33 && Math.floor((((this.duration/1000)/(self['recordData']['the_average_time'] *60)) *100)) > 0){
            this.$el.html($('<div class="progress-bar  bg-danger" id="progress" name="progressbar" role="progressbar" style="width:'+ Math.floor((((this.duration/1000)/(self['recordData']['the_average_time'] *60)) *100))+"%" + ';' + 'transition: .2s" aria-valuenow="25" aria-valuemin="0" aria-valuemax="100">' + Math.floor((((this.duration/1000)/(self['recordData']['the_average_time'] *60)) *100)) + '%' + '</div>'));
        }
        else{
            this.$el.html($('<i class="fa fa-flag" style="opacity: 1; transition: .5s; color: red"  id="co">'+ '' +'</i>'));
        }
    },
});
//var TimeCounter  = AbstractField.extend({
//    willStart: function () {
//        var self = this;
//        console.log(this.timer, "+++++++++++++++")
////        var progressBar = 0
//        const a = new Date(self.recordData.deadline._i)
//        const b = new Date()
//        console.log(a.getTime() - b.getTime(), 'VVVVVVVVVVVVVVVVVVVVVVVVVV')
////        if (a.getTime() - b.getTime() < 0) {
////            console.log('++_+_+__+_+_')
////            document.getElementById("co").style.opacity = "1"
////            document.getElementsByClassName("progress")[0].classList.add("d-none")
////            console.log('>><><><><><><><><><><>')
////        }
//        var def = this._rpc({
//            model: 'sci.maintenance.request',
//            method: 'search_read',
//            domain:  [['id', '=', this.res_id]],
//        }).then(function (result) {
//            console.log(result, 'aaaaaaaaaaaaaaaaaaaaaaaaaaaa')
//            var c1 = self['recordData']['completed_process'] * 60
//            console.log(c1, '++++++++++++++++++++')
////            var cobrb = startTimeCounter(function() {
////                var self = this;
////                console.log(self, 'selfselfselfselfselfselfselfselfselfselfself')
////                clearTimeout(this.timer);
////                if (self.duration) {
////                    this.duration -= 1;
////                    this.timer = setTimeout(function() {
////                        // your logic goes here
////                    }, 1000);
////                    this.$el.html($('<span>' +self.secondsToDhms(self.duration) + '</span>'));
////                }
////                else {
////                    this.$el.html($('<span>' +self.secondsToDhms(0.0) + '</span>'));
////                }
////            }),
////            c1--
////            this.timer = setTimeout(function() {
////            }, 1000);
////            c1 -= 1
//            var cobra = setInterval(function() {
//                c1--
//                console.log(c1, '<<<<<<<<<<<<<<<<<<<<<<<<<')
//                document.getElementById("progress").innerHTML =Math.floor((c1/((self['recordData']['the_average_time'] *60))*100))+"%"
//                document.getElementById("progress").style.width = Math.floor((c1/((self['recordData']['the_average_time'] *60))*100))+"%"
//                if(Math.floor((c1/((self['recordData']['the_average_time'] *60))*100)) <= 100 && Math.floor((c1/((self['recordData']['the_average_time'] *60))*100)) >= 66){
//                    document.getElementById("progress").classList.add("bg-success")
//                }
//                else if (Math.floor((c1/((self['recordData']['the_average_time'] *60))*100)) >= 33){
//                    document.getElementById("progress").classList.add("bg-warning")
//                }
//                else{
//                    document.getElementById("progress").classList.add("bg-danger")
//
//                }
//
//                if (Math.floor((c1/((self['recordData']['the_average_time'] *60))*100)) < 0) {
//                    window.clearInterval(cobra);
//                    document.getElementById("co").style.opacity = "1"
//                    document.getElementsByClassName("progress")[0].classList.add("d-none")
//                }
////                this.$el.html($('<span>' + moment.utc(c1).format("HH:mm:ss") + '</span>'));
////                rpc.query({
////                    model: 'sci.maintenance.request',
////                    method: 'rpc_render_completed_process',
////                    args: [[self.res_id], c1],
////                    });
//            }, 1000);
////            this.$el.html($('<div class="progress-bar  bg-success" id="progress" name="progressbar" role="progressbar" style="width: 100%; transition: .3s" aria-valuenow="25" aria-valuemin="0" aria-valuemax="100">' + Math.floor((c1/((self['recordData']['the_average_time'] *60))*100))+"%" + '</div>'));
//        });
//        console.log(def, '_______________________')
//
//        return $.when(this._super.apply(this, arguments), def);
//
//    },
//
////    startTimeCounter(function(){
////            var self = this;
////            console.log(self, 'selfselfselfselfselfselfselfselfselfselfself')
////            clearTimeout(this.timer);
////            if (self.duration) {
////                this.duration -= 1;
////                this.timer = setTimeout(function() {
////                	// your logic goes here
////                }, 1000);
////                this.$el.html($('<span>' +self.secondsToDhms(self.duration) + '</span>'));
////            }
////            else {
////            	this.$el.html($('<span>' +self.secondsToDhms(0.0) + '</span>'));
////            }
////        },
//});

field_registry.add('time_countdown', TimeCounter);
});


