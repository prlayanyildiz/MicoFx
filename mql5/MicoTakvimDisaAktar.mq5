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
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input int    GerideGun   = 900;                    // how far back to dump
input string CikisDosya  = "micofx_takvim.csv";    // under MQL5\Files
input int    EnAzOnem    = 1;                      // 0=none 1=low 2=moderate 3=high

//+------------------------------------------------------------------+
void OnStart()
{
   datetime bitis  = TimeCurrent() + 30 * 24 * 60 * 60;   // keep the near future too
   datetime baslar = TimeCurrent() - (datetime)GerideGun * 24 * 60 * 60;

   int fh = FileOpen(CikisDosya, FILE_WRITE | FILE_CSV | FILE_ANSI, ';');
   if(fh == INVALID_HANDLE)
   {
      Print("MicoTakvim: dosya acilamadi ", CikisDosya, " hata ", GetLastError());
      return;
   }

   FileWrite(fh, "time", "currency", "importance", "event_id", "event",
             "sector", "actual", "forecast", "previous", "unit");

   MqlCalendarValue values[];
   int toplam = CalendarValueHistory(values, baslar, bitis, NULL, NULL);
   if(toplam <= 0)
   {
      Print("MicoTakvim: takvim bos, hata ", GetLastError(),
            " - terminalde takvim kapali olabilir (Araclar > Secenekler > Sunucu)");
      FileClose(fh);
      return;
   }

   int yazilan = 0;
   for(int i = 0; i < toplam; i++)
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

      FileWrite(fh,
                (long)values[i].time,
                kur,
                (int)olay.importance,
                (long)olay.id,
                olay.name,
                EnumToString(olay.sector),
                gercek, beklen, onceki,
                olay.unit);
      yazilan++;
   }

   FileClose(fh);
   PrintFormat("MicoTakvim: %d kayittan %d yazildi -> MQL5\Files\%s",
               toplam, yazilan, CikisDosya);
}
//+------------------------------------------------------------------+
