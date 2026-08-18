//+------------------------------------------------------------------+
//| MicoTakvimDisaAktar.mq5                                          |
//| Dumps the terminal's economic calendar to CSV so the Python side |
//| can read it. The calendar lives only in MQL5 - the Python API    |
//| has no equivalent - so this is the only way across.              |
//|                                                                  |
//| Times are written as the raw MT5 integer, which is the server's  |
//| wall clock encoded as a Unix epoch, the same frame as bar and    |
//| deal stamps. Do not convert here; the Python side reads it with  |
//| sessions.server_datetime and nothing shifts.                     |
//|                                                                  |
//| Kept deliberately plain. An earlier version carried a duplicate  |
//| filter and a retry ladder and died with "Abnormal termination"   |
//| three chunks in; there is no point hardening an export until the |
//| calendar answers at all. MicoTakvimTeshis says whether it does.  |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input int    GerideGun   = 900;                    // how far back to dump
input string CikisDosya  = "micofx_takvim.csv";    // under MQL5\Files
input int    EnAzOnem    = 1;                      // 0=none 1=low 2=moderate 3=high
input int    ParcaGun    = 30;                     // days per request

//+------------------------------------------------------------------+
void OnStart()
{
   int fh = FileOpen(CikisDosya, FILE_WRITE | FILE_CSV | FILE_ANSI, ';');
   if(fh == INVALID_HANDLE)
   {
      PrintFormat("MicoTakvim: dosya acilamadi %s hata %d", CikisDosya, GetLastError());
      return;
   }
   FileWrite(fh, "time", "currency", "importance", "event_id", "event",
             "sector", "actual", "forecast", "previous", "unit");

   datetime bitis  = TimeCurrent() + 30 * 24 * 60 * 60;
   datetime baslar = TimeCurrent() - (datetime)GerideGun * 24 * 60 * 60;
   int      adim   = MathMax(1, ParcaGun) * 24 * 60 * 60;
   int      parca = 0, yazilan = 0, bos = 0, hatali = 0, sonHata = 0;

   for(datetime p0 = baslar; p0 < bitis; p0 += adim)
   {
      datetime p1 = p0 + adim;
      if(p1 > bitis)
         p1 = bitis;
      parca++;

      MqlCalendarValue values[];
      ResetLastError();
      int n = CalendarValueHistory(values, p0, p1, NULL, NULL);
      if(n <= 0)
      {
         int hata = GetLastError();
         if(hata != 0)
         {
            hatali++;
            sonHata = hata;
         }
         else
            bos++;
         continue;
      }

      for(int i = 0; i < n; i++)
      {
         MqlCalendarEvent olay;
         if(!CalendarEventById(values[i].event_id, olay))
            continue;
         if((int)olay.importance < EnAzOnem)
            continue;

         MqlCalendarCountry ulke;
         string kur = "";
         if(CalendarCountryById(olay.country_id, ulke))
            kur = ulke.currency;

         // has_value flags: an unreleased figure must read empty, not zero.
         string gercek = (values[i].HasActualValue())   ? DoubleToString(values[i].GetActualValue(), 6)   : "";
         string beklen = (values[i].HasForecastValue()) ? DoubleToString(values[i].GetForecastValue(), 6) : "";
         string onceki = (values[i].HasPreviousValue()) ? DoubleToString(values[i].GetPreviousValue(), 6) : "";

         FileWrite(fh, (long)values[i].time, kur, (int)olay.importance, (long)olay.id,
                   olay.name, EnumToString(olay.sector), gercek, beklen, onceki, olay.unit);
         yazilan++;
      }
   }

   FileClose(fh);
   PrintFormat("MicoTakvim: %d parca | %d yazildi | bos %d | hatali %d (son hata %d)",
               parca, yazilan, bos, hatali, sonHata);
   if(yazilan == 0)
      Print("MicoTakvim: hic kayit yok. Once MicoTakvimTeshis calistirin.");
}
//+------------------------------------------------------------------+
