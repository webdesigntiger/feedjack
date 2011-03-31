(function() {
  $(document).ready(function() {
    /* IE6? Fuck off */;    var fold_entries, folds, folds_commit, folds_lru, folds_update, limit, limit_lru, limit_lru_gc, storage_key, url_media, url_site, _ref, _ref2, _ref3;
    if (typeof localStorage == "undefined" || localStorage === null) {
      return;
    }
    /* size of lru journal to trigger gc */;
    limit_lru_gc = 300;
    /* size of lru journal after cleanup */;
    limit_lru = 200;
    /* minimum number of folds to keep */;
    limit = 100;
    Object.prototype.get_length = function() {
      var k, len, v;
      len = 0;
      for (k in this) {
        v = this[k];
        if (this.hasOwnProperty(k)) {
          len += 1;
        }
      }
      return len;
    };
    _ref = [$('html').data('url_site'), $('html').data('url_media')], url_site = _ref[0], url_media = _ref[1];
    storage_key = "feedjack.fold." + url_site;
    _ref2 = [localStorage["" + storage_key + ".folds"], localStorage["" + storage_key + ".folds_lru"]], folds = _ref2[0], folds_lru = _ref2[1];
    _ref3 = [folds ? JSON.parse(folds) : {}, folds_lru ? JSON.parse(folds_lru) : []], folds = _ref3[0], folds_lru = _ref3[1];
    folds_update = function(key, value) {
      if (value != null) {
        folds[key] = value;
        return folds_lru.push([key, value]);
      } else {
        return delete folds[key];
      }
    };
    folds_commit = function() {
      /* gc */;      var folds_lru_gc, key, len_folds, len_lru, val, _i, _len, _ref, _ref2;
      len_lru = folds_lru.length;
      if (len_lru > limit_lru_gc) {
        _ref = [folds_lru.slice(len_lru - limit_lru, (len_lru + 1) || 9e9), folds_lru.slice(0, len_lru - limit_lru)], folds_lru = _ref[0], folds_lru_gc = _ref[1];
        len_folds = folds.get_length() - limit;
        for (_i = 0, _len = folds_lru_gc.length; _i < _len; _i++) {
          _ref2 = folds_lru_gc[_i], key = _ref2[0], val = _ref2[1];
          if (len_folds <= 0) {
            break;
          }
          if (folds[key] === val) {
            folds_update(key);
            len_folds -= 1;
          }
        }
      }
      /* actual storage */;
      localStorage["" + storage_key + ".folds"] = JSON.stringify(folds);
      return localStorage["" + storage_key + ".folds_lru"] = JSON.stringify(folds_lru);
    };
    /* (un)fold everything under the specified day-header */;
    fold_entries = function(h1, fold, unfold) {
      var ts_day, ts_entry_max;
      if (fold == null) {
        fold = null;
      }
      if (unfold == null) {
        unfold = false;
      }
      h1 = $(h1);
      ts_day = h1.data('timestamp');
      ts_entry_max = 0;
      /* (un)fold entries */;
      h1.nextUntil('h1').children('.entry').each(function(idx, el) {
        var entry, ts;
        entry = $(el);
        ts = entry.data('timestamp');
        if (unfold === true) {
          entry.children('.content').css('display', '');
        } else if (fold !== false && folds[ts_day] >= ts) {
          entry.children('.content').css('display', 'none');
        }
        if ((!(folds[ts_day] != null) || folds[ts_day] < ts) && ts > ts_entry_max) {
          return ts_entry_max = ts;
        }
      });
      /* (un)fold whole day */;
      if (unfold === true) {
        h1.nextUntil('h1').css('display', '');
      } else if (fold !== false && (fold || ts_entry_max === 0)) {
        h1.nextUntil('h1').css('display', 'none');
      }
      return [ts_day, ts_entry_max];
    };
    /* Buttons, initial fold */;
    $('h1.feed').append("<img title=\"fold page\" class=\"button_fold_all\" src=\"" + url_media + "/fold_all.png\" />\n<img title=\"fold day\" class=\"button_fold\" src=\"" + url_media + "/fold.png\" />").each(function(idx, el) {
      return fold_entries(el);
    });
    /* Fold day button */;
    $('.button_fold').click(function(ev) {
      var h1, ts_day, ts_entry_max, _ref;
      h1 = $(ev.target).parent('h1');
      _ref = fold_entries(h1, false), ts_day = _ref[0], ts_entry_max = _ref[1];
      if (ts_entry_max > 0) {
        fold_entries(h1, true);
        folds_update(ts_day, Math.max(ts_entry_max, folds[ts_day] || 0));
      } else {
        fold_entries(h1, false, true);
        folds_update(ts_day);
      }
      return folds_commit();
    });
    /* Fold all button */;
    return $('.button_fold_all').click(function(ev) {
      var h1s, ts_page_max;
      ts_page_max = 0;
      h1s = $('h1.feed');
      h1s.each(function(idx, el) {
        return ts_page_max = Math.max(ts_page_max, fold_entries(el, false)[1]);
      });
      if (ts_page_max > 0) {
        h1s.each(function(idx, el) {
          var ts_day, ts_entry_max, _ref;
          _ref = fold_entries(el, true), ts_day = _ref[0], ts_entry_max = _ref[1];
          return folds_update(ts_day, Math.max(ts_entry_max, folds[ts_day] || 0));
        });
      } else {
        h1s.each(function(idx, el) {
          var ts_day, ts_entry_max, _ref;
          _ref = fold_entries(el, false, true), ts_day = _ref[0], ts_entry_max = _ref[1];
          return folds_update(ts_day);
        });
      }
      return folds_commit();
    });
  });
}).call(this);
